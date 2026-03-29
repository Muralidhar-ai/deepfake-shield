import pathlib
p = pathlib.Path(r"C:/Users/mural/AppData/Local/Programs/Python/Python314/Lib/site-packages/google/genai/types.py")
data = p.read_text()
i = data.find('class Part')
print('index', i)
print(data[i:i+1200])
