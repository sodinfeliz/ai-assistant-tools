import numpy as np


def color_generate(size, seed=None):
    if seed: np.random.seed(seed)
    return [np.random.randint(0, 256, 3).tolist() for _ in range(size)]





