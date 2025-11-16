#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HDF5 Data Manager - Enhanced Big Data Support

Provides efficient storage and retrieval for large simulation datasets.

Author: HydroClaude Development Team
Date: 2025-11-15
"""

import os
import sys

try:
    import h5py
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False
    h5py = None

import numpy as np
from typing import Dict, Any, Optional, List


class HDF5Manager:
    """
    Enhanced HDF5 data manager for big data support.
    
    Features:
    - Chunked storage for large datasets
    - Compression support
    - Metadata management
    - Incremental data writing
    - Efficient data retrieval
    """
    
    def __init__(self, filepath: str, mode: str = 'w', compression: str = 'gzip'):
        """
        Initialize HDF5 manager.
        
        Args:
            filepath: Path to HDF5 file
            mode: File mode ('w', 'r', 'a')
            compression: Compression algorithm ('gzip', 'lzf', None)
        """
        if not HDF5_AVAILABLE:
            raise ImportError(
                "h5py is required for HDF5 support. "
                "Install with: pip install h5py"
            )
        
        self.filepath = filepath
        self.mode = mode
        self.compression = compression
        self.file = None
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def open(self):
        """Open HDF5 file"""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.file = h5py.File(self.filepath, self.mode)
    
    def close(self):
        """Close HDF5 file"""
        if self.file:
            self.file.close()
            self.file = None
    
    def save_simulation_results(self, results: Dict[str, Any]):
        """
        Save complete simulation results to HDF5.
        
        Args:
            results: Simulation results dictionary
        """
        if not self.file:
            raise RuntimeError("HDF5 file not open")
        
        # Save metadata
        self._save_metadata(results)
        
        # Save universal data model
        if 'universal_data_model' in results:
            self._save_universal_model(results['universal_data_model'])
        
        # Save structures data
        if 'structures' in results:
            self._save_structures(results['structures'])
        
        # Save validation
        if 'validation' in results:
            self._save_validation(results['validation'])
    
    def _save_metadata(self, results: Dict[str, Any]):
        """Save metadata as attributes"""
        meta_group = self.file.create_group('metadata')
        
        # Simulation info
        if 'simulation' in results:
            for key, value in results['simulation'].items():
                if isinstance(value, (int, float, str, bool)):
                    meta_group.attrs[f'sim_{key}'] = value
        
        # Canal info
        if 'canal' in results:
            for key, value in results['canal'].items():
                if isinstance(value, (int, float, str, bool)):
                    meta_group.attrs[f'canal_{key}'] = value
        
        # Solver info
        if 'solver' in results:
            for key, value in results['solver'].items():
                if isinstance(value, (int, float, str, bool)):
                    meta_group.attrs[f'solver_{key}'] = value
    
    def _save_universal_model(self, model: Dict[str, Any]):
        """Save universal data model with chunking and compression"""
        udm_group = self.file.create_group('universal_data_model')
        
        # Save dimensions
        dims = model.get('dimensions', {})
        dim_group = udm_group.create_group('dimensions')
        for key, value in dims.items():
            if value is not None:
                dim_group.attrs[key] = value
        
        # Save data with chunking and compression
        data = model.get('data', {})
        data_group = udm_group.create_group('data')
        
        # Spatial data
        if 'spatial' in data:
            self._save_dataset(
                data_group, 'spatial', data['spatial'],
                description='Spatial profile data'
            )
        
        # Temporal data (for unsteady simulations)
        if 'temporal' in data and data['temporal'] is not None:
            self._save_dataset(
                data_group, 'temporal', data['temporal'],
                description='Temporal series data'
            )
        
        # Variables metadata
        if 'variables' in dims:
            var_list = dims['variables']
            dt = h5py.special_dtype(vlen=str)
            var_dataset = data_group.create_dataset(
                'variables', 
                (len(var_list),), 
                dtype=dt
            )
            var_dataset[:] = var_list
    
    def _save_dataset(self, group, name: str, data: Dict[str, np.ndarray], 
                     description: str = ""):
        """
        Save dataset with optimal chunking and compression.
        
        Args:
            group: HDF5 group
            name: Dataset name
            data: Dictionary of numpy arrays
            description: Dataset description
        """
        subgroup = group.create_group(name)
        subgroup.attrs['description'] = description
        
        for var_name, var_data in data.items():
            if isinstance(var_data, np.ndarray):
                # Determine optimal chunk size
                chunks = self._get_optimal_chunks(var_data.shape)
                
                # Create dataset with compression
                dataset = subgroup.create_dataset(
                    var_name,
                    data=var_data,
                    chunks=chunks,
                    compression=self.compression,
                    compression_opts=6 if self.compression == 'gzip' else None
                )
                
                # Add variable metadata
                dataset.attrs['units'] = self._get_variable_units(var_name)
                dataset.attrs['description'] = self._get_variable_description(var_name)
    
    def _save_structures(self, structures: List[Dict[str, Any]]):
        """Save hydraulic structures data"""
        if not structures:
            return
        
        struct_group = self.file.create_group('structures')
        
        for i, struct in enumerate(structures):
            s_group = struct_group.create_group(f'structure_{i}')
            
            # Save basic info
            for key, value in struct.items():
                if isinstance(value, (int, float, str, bool)):
                    s_group.attrs[key] = value
                elif isinstance(value, dict):
                    # Save nested data
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float, str, bool)):
                            s_group.attrs[f'{key}_{sub_key}'] = sub_value
    
    def _save_validation(self, validation: Dict[str, Any]):
        """Save validation results"""
        val_group = self.file.create_group('validation')
        
        for key, value in validation.items():
            if isinstance(value, (int, float, str, bool)):
                val_group.attrs[key] = value
            elif isinstance(value, np.ndarray):
                val_group.create_dataset(key, data=value)
    
    def _get_optimal_chunks(self, shape: tuple) -> tuple:
        """
        Calculate optimal chunk size for dataset.
        
        Args:
            shape: Array shape
            
        Returns:
            Optimal chunk size
        """
        if len(shape) == 1:
            # 1D array: use chunks of ~100KB
            chunk_size = min(10000, shape[0])
            return (chunk_size,)
        elif len(shape) == 2:
            # 2D array: balance between row and column access
            chunk_rows = min(1000, shape[0])
            chunk_cols = shape[1]  # Keep all columns together
            return (chunk_rows, chunk_cols)
        else:
            # Higher dimensions: use default
            return True
    
    def _get_variable_units(self, var_name: str) -> str:
        """Get units for variable"""
        units_map = {
            'depth': 'm',
            'velocity': 'm/s',
            'discharge': 'm³/s',
            'froude': '-',
            'energy': 'm',
            'position': 'm',
            'time': 's',
            'elevation': 'm',
            'width': 'm',
            'area': 'm²',
            'wetted_perimeter': 'm',
            'hydraulic_radius': 'm',
        }
        return units_map.get(var_name, '-')
    
    def _get_variable_description(self, var_name: str) -> str:
        """Get description for variable"""
        desc_map = {
            'depth': 'Water depth',
            'velocity': 'Flow velocity',
            'discharge': 'Discharge (flow rate)',
            'froude': 'Froude number',
            'energy': 'Specific energy',
            'position': 'Spatial position',
            'time': 'Time',
            'elevation': 'Water surface elevation',
            'width': 'Channel width',
            'area': 'Cross-sectional area',
            'wetted_perimeter': 'Wetted perimeter',
            'hydraulic_radius': 'Hydraulic radius',
        }
        return desc_map.get(var_name, '')
    
    def load_simulation_results(self) -> Dict[str, Any]:
        """
        Load complete simulation results from HDF5.
        
        Returns:
            Results dictionary
        """
        if not self.file:
            raise RuntimeError("HDF5 file not open")
        
        results = {}
        
        # Load metadata
        if 'metadata' in self.file:
            results.update(self._load_metadata())
        
        # Load universal data model
        if 'universal_data_model' in self.file:
            results['universal_data_model'] = self._load_universal_model()
        
        # Load structures
        if 'structures' in self.file:
            results['structures'] = self._load_structures()
        
        # Load validation
        if 'validation' in self.file:
            results['validation'] = self._load_validation()
        
        return results
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from attributes"""
        meta_group = self.file['metadata']
        
        simulation = {}
        canal = {}
        solver = {}
        
        for key, value in meta_group.attrs.items():
            if key.startswith('sim_'):
                simulation[key[4:]] = value
            elif key.startswith('canal_'):
                canal[key[6:]] = value
            elif key.startswith('solver_'):
                solver[key[7:]] = value
        
        return {
            'simulation': simulation,
            'canal': canal,
            'solver': solver
        }
    
    def _load_universal_model(self) -> Dict[str, Any]:
        """Load universal data model"""
        udm_group = self.file['universal_data_model']
        
        # Load dimensions
        dimensions = {}
        if 'dimensions' in udm_group:
            dim_group = udm_group['dimensions']
            for key, value in dim_group.attrs.items():
                dimensions[key] = value
        
        # Load variables list
        if 'data/variables' in udm_group:
            dimensions['variables'] = list(udm_group['data/variables'][:])
        
        # Load data
        data = {}
        if 'data/spatial' in udm_group:
            data['spatial'] = self._load_dataset(udm_group['data/spatial'])
        
        if 'data/temporal' in udm_group:
            data['temporal'] = self._load_dataset(udm_group['data/temporal'])
        
        return {
            'dimensions': dimensions,
            'data': data
        }
    
    def _load_dataset(self, group) -> Dict[str, np.ndarray]:
        """Load dataset from HDF5 group"""
        data = {}
        for key in group.keys():
            if key != 'variables':
                data[key] = group[key][:]
        return data
    
    def _load_structures(self) -> List[Dict[str, Any]]:
        """Load hydraulic structures"""
        struct_group = self.file['structures']
        structures = []
        
        for key in sorted(struct_group.keys()):
            s_group = struct_group[key]
            struct = dict(s_group.attrs)
            structures.append(struct)
        
        return structures
    
    def _load_validation(self) -> Dict[str, Any]:
        """Load validation results"""
        val_group = self.file['validation']
        validation = dict(val_group.attrs)
        
        # Load array data
        for key in val_group.keys():
            validation[key] = val_group[key][:]
        
        return validation
    
    @staticmethod
    def get_file_info(filepath: str) -> Dict[str, Any]:
        """
        Get information about HDF5 file without loading all data.
        
        Args:
            filepath: Path to HDF5 file
            
        Returns:
            File information dictionary
        """
        if not HDF5_AVAILABLE:
            raise ImportError("h5py is required")
        
        info = {
            'filepath': filepath,
            'file_size': os.path.getsize(filepath),
            'groups': [],
            'datasets': []
        }
        
        with h5py.File(filepath, 'r') as f:
            def visit_func(name, obj):
                if isinstance(obj, h5py.Group):
                    info['groups'].append(name)
                elif isinstance(obj, h5py.Dataset):
                    info['datasets'].append({
                        'name': name,
                        'shape': obj.shape,
                        'dtype': str(obj.dtype),
                        'size': obj.size
                    })
            
            f.visititems(visit_func)
        
        return info


def check_hdf5_available() -> bool:
    """Check if HDF5 support is available"""
    return HDF5_AVAILABLE


if __name__ == '__main__':
    # Test HDF5 manager
    print("HDF5 Manager Test")
    print(f"HDF5 Available: {check_hdf5_available()}")
    
    if check_hdf5_available():
        # Create test data
        test_results = {
            'simulation': {'type': 'steady', 'mode': 'single_canal'},
            'canal': {'length': 1000, 'width': 10},
            'universal_data_model': {
                'dimensions': {
                    'spatial': 100,
                    'temporal': None,
                    'variables': ['depth', 'velocity', 'froude']
                },
                'data': {
                    'spatial': {
                        'position': np.linspace(0, 1000, 100),
                        'depth': np.random.rand(100) * 2 + 1,
                        'velocity': np.random.rand(100) * 1 + 0.5,
                        'froude': np.random.rand(100) * 0.5
                    }
                }
            }
        }
        
        # Test save
        test_file = 'test_results.h5'
        with HDF5Manager(test_file, 'w') as hdf:
            hdf.save_simulation_results(test_results)
        
        print(f"✅ Test file created: {test_file}")
        
        # Test load
        with HDF5Manager(test_file, 'r') as hdf:
            loaded = hdf.load_simulation_results()
        
        print("✅ Data loaded successfully")
        
        # Test file info
        info = HDF5Manager.get_file_info(test_file)
        print(f"✅ File info: {len(info['groups'])} groups, {len(info['datasets'])} datasets")
        
        # Cleanup
        os.remove(test_file)
        print("✅ Test completed")
    else:
        print("⚠️  Install h5py to use HDF5 features: pip install h5py")
