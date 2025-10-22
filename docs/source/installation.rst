Installation
============

Requirements
------------

* Python 3.8+
* NumPy >= 1.21.0
* SciPy >= 1.7.0
* Matplotlib >= 3.4.0
* NetworkX >= 2.6.0
* PyYAML >= 5.4.0

Basic Installation
------------------

Install from source:

.. code-block:: bash

   git clone https://github.com/leixiaohui-1974/HydroClaude.git
   cd HydroClaude
   pip install -e .

Development Installation
------------------------

For development with all optional dependencies:

.. code-block:: bash

   pip install -e .[dev,logging]

This includes:

* **dev**: pytest, black, flake8
* **logging**: colorlog for colored console output

Documentation Build
-------------------

To build this documentation:

.. code-block:: bash

   pip install -e .[docs]
   cd docs
   make html

Verification
------------

Test your installation:

.. code-block:: bash

   pytest tests/

Expected output: 164/164 tests passing

Or run the benchmark suite:

.. code-block:: bash

   hydroclaude-benchmark --quick

