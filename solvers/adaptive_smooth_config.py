#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""




: Claude
: 2025-10-23
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class AdaptiveSmoothConfig:
    """
    

    
    - 'fixed': 
    - 'residual': 
    - 'distance': 
    - 'hybrid': 
    """

    # 
    mode: Literal['fixed', 'residual', 'distance', 'hybrid'] = 'hybrid'

    # 
    smooth_weight_min: float = 0.25  # /
    smooth_weight_max: float = 0.75  # /

    # 
    fixed_weight: float = 0.55  # mode='fixed'

    # 
    characteristic_length: float = 150.0  #  (m)

    # 
    residual_scale: float = 0.03  # 
    residual_high_threshold: float = 0.05  # 
    residual_medium_threshold: float = 0.02  # 

    # 
    alpha: float = 0.6  # 
    beta: float = 0.4   # 

    def __post_init__(self):
        """"""
        # 
        if self.mode not in ['fixed', 'residual', 'distance', 'hybrid']:
            raise ValueError(f"Invalid mode: {self.mode}")

        # 
        if not (0.0 <= self.smooth_weight_min <= 1.0):
            raise ValueError(f"smooth_weight_min must be in [0, 1], got {self.smooth_weight_min}")
        if not (0.0 <= self.smooth_weight_max <= 1.0):
            raise ValueError(f"smooth_weight_max must be in [0, 1], got {self.smooth_weight_max}")
        if self.smooth_weight_min > self.smooth_weight_max:
            raise ValueError("smooth_weight_min must be <= smooth_weight_max")

        # 
        if self.mode == 'hybrid':
            if abs(self.alpha + self.beta - 1.0) > 1e-6:
                # 
                total = self.alpha + self.beta
                if total > 0:
                    self.alpha /= total
                    self.beta /= total
                else:
                    raise ValueError("alpha and beta must sum to 1.0 (or be positive)")

    def __repr__(self):
        """"""
        if self.mode == 'fixed':
            return f"AdaptiveSmoothConfig(mode='fixed', weight={self.fixed_weight})"
        elif self.mode == 'residual':
            return (f"AdaptiveSmoothConfig(mode='residual', "
                   f"range=[{self.smooth_weight_min}, {self.smooth_weight_max}])")
        elif self.mode == 'distance':
            return (f"AdaptiveSmoothConfig(mode='distance', "
                   f"range=[{self.smooth_weight_min}, {self.smooth_weight_max}], "
                   f"L_char={self.characteristic_length}m)")
        else:  # hybrid
            return (f"AdaptiveSmoothConfig(mode='hybrid', "
                   f"range=[{self.smooth_weight_min}, {self.smooth_weight_max}], "
                   f"α={self.alpha:.2f}, β={self.beta:.2f})")


# 
DEFAULT_CONFIG = AdaptiveSmoothConfig(mode='fixed', fixed_weight=0.55)

AGGRESSIVE_CONFIG = AdaptiveSmoothConfig(
    mode='hybrid',
    smooth_weight_min=0.20,
    smooth_weight_max=0.80,
    alpha=0.5,
    beta=0.5
)

CONSERVATIVE_CONFIG = AdaptiveSmoothConfig(
    mode='hybrid',
    smooth_weight_min=0.30,
    smooth_weight_max=0.70,
    alpha=0.7,
    beta=0.3
)

DISTANCE_ONLY_CONFIG = AdaptiveSmoothConfig(
    mode='distance',
    smooth_weight_min=0.25,
    smooth_weight_max=0.75,
    characteristic_length=150.0
)

RESIDUAL_ONLY_CONFIG = AdaptiveSmoothConfig(
    mode='residual',
    smooth_weight_min=0.25,
    smooth_weight_max=0.75,
    residual_scale=0.03
)
