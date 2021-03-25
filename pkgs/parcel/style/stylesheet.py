from pathlib import Path


def connect_to_stylesheet(fn, dir=None):
    if dir is None:
        dir = Path('GUI/stylesheet/')
    else: 
        dir = Path(dir)

    full_path = dir.joinpath(f'{fn}.txt')
    if not full_path.exists():
        raise FileExistsError(f'{fn} not exist in {str(dir)}.')
    else:
        lines = open(str(full_path), 'r').readlines()
        return ' '.join([line.strip() for line in lines])
