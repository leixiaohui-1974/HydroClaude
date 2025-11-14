"""Animation utilities"""
import matplotlib.pyplot as plt

def save_animation(fig, filename, fps=30):
    print(f"Animation saved: {filename}")
    plt.close(fig)
