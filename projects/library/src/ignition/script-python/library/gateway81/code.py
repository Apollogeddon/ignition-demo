"""The 8.1 gateway's configuration store, for library.seed.

8.1 has no configuration API, so this uses the gateway's own persistence
layer, the one its web UI saves through: each profile (user source, journal,
audit profile, ...) is a record of a type its manager registers, plus a
settings record for that type. Only library.seed calls this, and only on 8.1;
8.3 is configured through its REST API instead.
"""
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportMissingModuleSource=false

import json
import time

import java.lang
from com.inductiveautomation.ignition.gateway import IgnitionGateway
from simpleorm.dataset import SQuery
from system.db import addDatasource, getConnections
from system.user import addRole, addUser, getNewUser, getRoles, getUsers

MYPY = False
if MYPY:
	from typing import Any, Dict, List, Optional

# section -> (profile record class, the manager that registers its types)
PROFILES = {
	"userSources": (
		"com.inductiveautomation.ignition.gateway.user.UserSourceProfileRecord",
		lambda ctx: ctx.getUserSourceManager(),
	),
	"alarmJournals": (
		"com.inductiveautomation.ignition.gateway.alarming.config.AlarmJournalRecord",
		lambda ctx: ctx.getAlarmManager().getJournalManager(),
	),
	"auditProfiles": (
		"com.inductiveautomation.ignition.gateway.audit.AuditProfileRecord",
		lambda ctx: ctx.getAuditManager(),
	),
	"emailProfiles": (
		"com.inductiveautomation.ignition.gateway.mail.EmailProfileSettingsRecord",
		lambda ctx: ctx.getEmailProfileManager(),
	),
	"alarmNotificationProfiles": (
		"com.inductiveautomation.ignition.alarming.notification.AlarmNotificationProfileRecord",
		None,
	),
}

# settings records of module types whose manager is not reachable from here
MODULE_SETTINGS = {
	"EmailNotificationProfileType": (
		"com.inductiveautomation.ignition.alarming.notification.email.EmailNotificationSettingsRecord"
	),
}

IDP_RECORD = "com.inductiveautomation.ignition.gateway.auth.idp.IdpAdapterRecord"
SYSPROPS_RECORD = "com.inductiveautomation.ignition.gateway.model.SystemPropertiesRecord"
SECURITY_LEVEL = "com.inductiveautomation.ignition.common.auth.security.level.SecurityLevelConfig"

# an Ignition IdP backed by a user source, as the gateway creates "default"
IDP_TEMPLATE = {
	"authStrategy": {
		"type": "ignition",
		"config": {
			"version": 1,
			"authMethods": ["username-and-password"],
			"defaultAuthMethod": "username-and-password",
			"badgeSecret": False,
			"sessionInactivityTimeout": 30,
			"sessionExp": 0,
			"rememberMeExp": 0,
		},
	},
	"userAttributeMapper": {
		"id": {"type": "direct", "config": {"attributePath": "sub"}},
		"userName": {"type": "direct", "config": {"attributePath": "preferred_username"}},
		"firstName": {"type": "direct", "config": {"attributePath": "given_name"}},
		"lastName": {"type": "direct", "config": {"attributePath": "family_name"}},
		"email": {"type": "direct", "config": {"attributePath": "email"}},
		"roles": {"type": "direct", "config": {"attributePath": "roles"}},
	},
	"directSecurityLevelPolicies": {"id": {}, "username": {}},
	"derivedSecurityLevelPolicies": [],
}


class Gateway81(object):
	"""library.seed's adapter for an 8.1 gateway (existing / create per section)."""

	def __init__(self):
		# type: () -> None
		self.ctx = IgnitionGateway.get()
		self.pi = self.ctx.getPersistenceInterface()

	# -- records ---------------------------------------------------------
	def recordClass(self, name):
		# type: (str) -> Any
		try:
			return java.lang.Class.forName(name)
		except java.lang.ClassNotFoundException:
			return self.ctx.getModuleManager().resolveClass(name)

	def meta(self, name):
		# type: (str) -> Any
		return self.recordClass(name).getField("META").get(None)

	def field(self, meta, name):
		# type: (Any, str) -> Any
		for f in meta.getFieldMetas():
			if str(f.getFieldName()) == name:
				return f
		msg = "{} has no field {}".format(meta.getTableName(), name)
		raise ValueError(msg)

	def records(self, meta):
		# type: (Any) -> List[Any]
		return list(self.pi.query(SQuery(meta)))

	def named(self, meta, name):
		# type: (Any, str) -> Any
		nameField = self.field(meta, "Name")
		for rec in self.records(meta):
			if rec.getString(nameField) == name:
				return rec
		msg = "no {} named {}".format(meta.getTableName(), name)
		raise ValueError(msg)

	def setFields(self, rec, meta, values):
		# type: (Any, Any, Dict[str, Any]) -> None
		"""Set record fields by name, converting to each field's type."""
		for name, value in values.items():
			f = self.field(meta, name)
			kind = f.getClass().getSimpleName()
			if value is None:
				rec.setNull(f)
			elif kind == "ReferenceField":
				rec.setReference(f, self.named(f.getReferencedRecordMeta(), value))
			elif kind == "EnumField":
				rec.setEnum(f, java.lang.Enum.valueOf(f.getEnumClass(), value))
			elif kind == "BooleanField":
				rec.setBoolean(f, bool(value))
			elif kind == "IntField":
				rec.setInt(f, int(value))
			elif kind == "LongField":
				rec.setLong(f, int(value))
			else:
				rec.setString(f, value)

	def createProfile(self, section, name, item):
		# type: (str, str, Dict[str, Any]) -> Any
		className, manager = PROFILES[section]
		meta = self.meta(className)
		profile = self.pi.createNew(meta)
		fields = {"Name": name, "Type": item["type"]}
		fields.update(item.get("profile") or {})
		# saved disabled first: its manager starts an enabled profile as soon as
		# it is added, before the settings record below exists
		hasEnabled = any(str(f.getFieldName()) == "Enabled" for f in meta.getFieldMetas())
		enabled = fields.pop("Enabled", True)
		if hasEnabled:
			fields["Enabled"] = False
		self.setFields(profile, meta, fields)
		self.pi.save(profile)
		if manager is not None:
			settingsMeta = manager(self.ctx).getExtensionPoint(item["type"]).getSettingsRecordType()
		elif item["type"] in MODULE_SETTINGS:
			settingsMeta = self.meta(MODULE_SETTINGS[item["type"]])
		else:
			settingsMeta = None
		if settingsMeta is not None:
			settings = self.pi.createNew(settingsMeta)
			settings.setLong(self.field(settingsMeta, "ProfileId"), profile.getId())
			self.setFields(settings, settingsMeta, item.get("settings") or {})
			self.pi.save(settings)
		if hasEnabled and enabled:
			# an ordinary update, as the web UI makes: the manager starts it now
			self.setFields(profile, meta, {"Enabled": True})
			self.pi.save(profile)
		elif not hasEnabled and settingsMeta is not None:
			# no Enabled field (audit profiles): the manager started it without
			# settings; two real updates restart it with them
			description = self.field(meta, "Description")
			text = profile.getString(description) or ""
			profile.setString(description, text + " ")
			self.pi.save(profile)
			profile.setString(description, text)
			self.pi.save(profile)
		return profile

	# -- library.seed adapter ----------------------------------------------
	def existing(self, section):
		# type: (str) -> List[str]
		"""Return the names already configured in a section."""
		if section == "databases":
			dataset = getConnections()
			return [str(dataset.getValueAt(row, "Name")) for row in range(dataset.getRowCount())]
		if section in PROFILES:
			meta = self.meta(PROFILES[section][0])
			nameField = self.field(meta, "Name")
			return [str(rec.getString(nameField)) for rec in self.records(meta)]
		if section == "identityProviders":
			meta = self.meta(IDP_RECORD)
			return [json.loads(self.idpConfig(rec, meta))["name"] for rec in self.records(meta)]
		if section == "securityLevels":
			return [
				str(level.getName())
				for level in self.ctx.getSecurityLevelManager().getSecurityLevelsConfig()
			]
		return []

	def idpConfig(self, rec, meta):
		# type: (Any, Any) -> str
		return str(java.lang.String(rec.getBytes(self.field(meta, "CONFIG")), "UTF-8"))

	def create(self, section, name, item):
		# type: (str, str, Dict[str, Any]) -> Optional[bool]
		"""Create one item of a section; False when there was nothing to change."""
		if section == "databases":
			addDatasource(
				item.get("driver", "PostgreSQL"),
				name,
				item.get("description", ""),
				item["url"],
				item.get("user"),
				item.get("password"),
			)
		elif section == "userSources":
			self.createProfile(section, name, item)
			self.addRolesAndUsers(name, item)
		elif section in PROFILES:
			self.createProfile(section, name, item)
		elif section == "identityProviders":
			self.createIdp(name, item)
		elif section == "securityLevels":
			self.createSecurityLevel(name, item)
		elif section == "gateway":
			return self.updateSystemSettings(item)
		else:
			msg = "unknown section {}".format(section)
			raise ValueError(msg)
		return None

	def addRolesAndUsers(self, source, item):
		# type: (str, Dict[str, Any]) -> None
		"""Add roles and users once the new user source has started."""
		for _ in range(20):
			try:
				getRoles(source)
				break
			except (Exception, java.lang.Throwable):  # noqa: BLE001
				time.sleep(0.5)
		for role in item.get("roles") or []:
			if role not in getRoles(source):
				addRole(source, role)
		existing = [str(u.get("username")) for u in getUsers(source)]
		for spec in item.get("users") or []:
			if spec["name"] in existing:
				continue
			user = getNewUser(source, spec["name"])
			user.set("password", spec["password"])
			for key in ("firstname", "lastname"):
				if key in spec:
					user.set(key, spec[key])
			user.addRoles(spec.get("roles") or [])
			response = addUser(source, user)
			errors = list(response.getErrors()) if response is not None else []
			if errors:
				msg = "user {}: {}".format(spec["name"], "; ".join(str(e) for e in errors))
				raise ValueError(msg)

	def createIdp(self, name, item):
		# type: (str, Dict[str, Any]) -> None
		config = json.loads(json.dumps(IDP_TEMPLATE))
		config["name"] = name
		config["description"] = item.get("description", "")
		config["authStrategy"]["config"]["userSource"] = item["userSource"]
		meta = self.meta(IDP_RECORD)
		rec = self.pi.createNew(meta)
		rec.setBytes(
			self.field(meta, "CONFIG"), java.lang.String(json.dumps(config)).getBytes("UTF-8")
		)
		self.pi.save(rec)

	def createSecurityLevel(self, name, item):
		# type: (str, Dict[str, Any]) -> None
		from com.google.common.collect import ImmutableSet

		level = dict(item, name=name)
		manager = self.ctx.getSecurityLevelManager()
		config = (
			self.recordClass(SECURITY_LEVEL)
			.getMethod("fromJson", java.lang.String)
			.invoke(None, json.dumps(level))
		)
		manager.updateSecurityLevelsConfig(
			ImmutableSet.copyOf(list(manager.getSecurityLevelsConfig()) + [config])
		)

	def updateSystemSettings(self, item):
		# type: (Dict[str, Any]) -> bool
		"""Set the system settings that differ; return whether any did."""
		meta = self.meta(SYSPROPS_RECORD)
		rec = self.records(meta)[0]
		wanted = {}
		if "auditProfile" in item:
			wanted["GatewayAuditProfile"] = item["auditProfile"]
		changed = {k: v for k, v in wanted.items() if rec.getString(self.field(meta, k)) != v}
		if not changed:
			return False
		self.setFields(rec, meta, changed)
		self.pi.save(rec)
		return True
