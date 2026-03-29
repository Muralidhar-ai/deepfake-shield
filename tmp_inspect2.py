import pathlib
p = pathlib.Path('C:/Users/mural/AppData/Local/Programs/Python/Python314/Lib/site-packages/google/genai/types.py')
text = p.read_text()
lines = text.splitlines()
for idx, line in enumerate(lines, 1):
    if line.strip().startswith('class Part'):
        print('line', idx)
        for j in range(idx-2, idx+40):
            if 1 <= j <= len(lines):
                print(f'{j:5d}:', lines[j-1])
        break
