-- Example rows for the asset summary view.

INSERT INTO area (name, description) VALUES
    ('North', 'Intake and pumping'),
    ('South', 'Treatment'),
    ('East',  'Storage');

INSERT INTO asset (id, name, area, kind) VALUES
    (1, 'Intake pump 1',   'North', 'pump'),
    (2, 'Intake pump 2',   'North', 'pump'),
    (3, 'Blower 1',        'South', 'blower'),
    (4, 'Dosing pump',     'South', 'pump'),
    (5, 'Mixer',           'South', 'mixer'),
    (6, 'Reservoir level', 'East',  'level');
