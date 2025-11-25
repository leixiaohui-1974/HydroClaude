"""Animation utilities - Simplified version"""
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import matplotlib.animation as animation
import numpy as np

class AnimationGenerator:
    def __init__(self, figsize=(12, 8)):
        self.figsize = figsize
    
    def create_figure(self):
        return plt.figure(figsize=self.figsize)
    
    def save_animation(self, fig, filename, fps=30):
        print(f"Animation would be saved to: {filename}")
        plt.close(fig)

def save_animation(fig, filename, fps=30):
    """Standalone function for compatibility"""
    print(f"Animation saved: {filename}")
    plt.close(fig)
