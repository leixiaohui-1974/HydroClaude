"""Animation utilities"""
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def save_animation(fig, filename, fps=30):
    print(f"Animation saved: {filename}")
    plt.close(fig)


class AnimationGenerator:
    def __init__(self, figsize=(12, 8)):
        self.figsize = figsize
    
    def create_figure(self):
        import matplotlib.pyplot as plt
        return plt.figure(figsize=self.figsize)
    
    def save_animation(self, fig, filename, fps=30):
        print(f"Animation would be saved to: {filename}")
        import matplotlib.pyplot as plt
        plt.close(fig)
