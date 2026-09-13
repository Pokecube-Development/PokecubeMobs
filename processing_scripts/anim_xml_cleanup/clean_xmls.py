import xml.etree.ElementTree as ET
import os

input_dir = "./old"
output_dir = "./cleaned"
for filename in os.listdir(input_dir):
    _file = f"{input_dir}/{filename}"
    data = ET.parse(_file)
    model = data.findall("model")[0]
    for obj in model.findall("phase"):
        attr = obj.attrib
        if not 'name' in attr or attr['name'] != 'global':
            model.remove(obj)
    _file = f"{output_dir}/{filename}"
    # ET.dump(data)
    str = ET.tostring(data.getroot()).decode()
    with open(_file, 'w') as f:
        f.write(str)