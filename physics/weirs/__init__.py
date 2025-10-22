#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
堰类水工建筑物模块

包含各种类型的堰：
- 宽顶堰 (Broad-crested weir)
- 薄壁堰 (Sharp-crested weir)
- 侧堰 (Side weir)

作者: Claude
日期: 2025-10-22
"""

from .broad_crested_weir import BroadCrestedWeir
from .sharp_crested_weir import SharpCrestedWeir
from .side_weir import SideWeir

__all__ = [
    'BroadCrestedWeir',
    'SharpCrestedWeir',
    'SideWeir',
]
