import csv

template = "%(field_name)s = models.%(field_type)s(%(options)s)"

field_type_map = {
    'char': 'CharField',
    'Boolean':'NullBooleanField',
    'int':'IntegerField',
    'float':'FloatField',
    }

default_options = {
    'CharField': {'max_length': 200}
}

fields_default_order = []
fields_order = {}

def get_field_type(field_format):
    extra_options = {}
    if field_format == '':
        return 'CharField', extra_options
    if field_format.startswith('['):
        field_format = eval(field_format)
        choices = [(''.join(l for l in f if l.isalnum()).lower(), f) for f in field_format]
        extra_options['max_length'] = 2
        extra_options['choices'] = choices
        return 'CharField', extra_options
    else:
        return field_type_map[field_format], extra_options

print '-' * 80
print 'Study Model'
print '-' * 80

with open('metadata_neurovault.csv', 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    header = reader.next()
    for row in reader:
        field = {}
        field_options = {}
        field_infos = dict(zip(header, row))

        field_type, extras = get_field_type(field_infos['Format'])
        field_options.update(extras)
        field_options.update(default_options.get(field_type, {}))

        field['field_name'] = field_infos['Item']
        field['field_type'] = field_type

        try:
            priority = int(field_infos['Priority (1=required, 2=recommended,3=optional)'])
        except:
            priority = 3

        if priority == 1:
            field_options['null'] = False
            field_options['blank'] = False
        else:
            field_options['null'] = True
            field_options['blank'] = True


        field_options['help_text'] = '"%s"' % field_infos['Verbose description']
        field_options['verbose_name'] = '"%s.%s"' % (field_infos['Section'], field_infos['Item'])
        fields_order.setdefault(priority, []).append('%s.%s' % (field_infos['Section'], field_infos['Item']))

        field['options'] = ', '.join(['%s=%s' % (k, v) for k, v in field_options.items()])
        print '    %s' % template % field

print 
print '-' * 80
print 'Study Form'
print '-' * 80

template = "self.fields.keyOrder = [%s]"

order = []

for priority in sorted(fields_order.keys()):
    order.extend([f.split('.')[1] for f in sorted(fields_order[priority])])

print template % ', '.join(["'%s'" % f for f in order])
# print fields_order
