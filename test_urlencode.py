import urllib.parse

data = {
    'entry.111': 'Option A',
    'entry.222': ['Val 1', 'Val 2'],
    'pageHistory': '0'
}

encoded = urllib.parse.urlencode(data, doseq=True)
print("Encoded payload:", encoded)
