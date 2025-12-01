from pathlib import Path
path = Path('frontend/pages/08_Gestion_Alumnos.py')
lines = path.read_text(encoding='utf-8').splitlines()

def repl(predicate, new_line):
    for idx, line in enumerate(lines):
        if predicate(line):
            lines[idx] = new_line
            return
    raise SystemExit(f'Line not found for replacement: {new_line}')

repl(lambda l: 'st.set_page_config' in l and 'Gest' in l, '    st.set_page_config(page_title="Gesti\\u00f3n de Alumnos", page_icon="\\U0001F4DA", layout="wide")')
repl(lambda l: 'st.title(' in l, '    st.title("Gesti\\u00f3n de Alumnos")')
repl(lambda l: 'number_input("A' in l, '    y = c2.number_input("A\\u00f1o", min_value=2000, max_value=2100, value=date.today().year, step=1)')
repl(lambda l: 'text_input("Secci' in l, '    s = c4.text_input("Secci\\u00f3n", max_chars=2, value="A")')
repl(lambda l: 'navega a la' in l, '    # Crear nuevo alumno: navega a la p\\u00e1gina unificada de edici\\u00f3n/creaci\\u00f3n')
repl(lambda l: 'c3.caption' in l and 'G' in l, '            c3.caption(f"G\\u00e9nero: {stu.get(\'gender\',\'\') or \"-\"}")')

path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
