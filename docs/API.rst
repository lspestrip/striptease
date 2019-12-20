API documentation
=================

Basic operations and connections
--------------------------------

.. automodule:: striptease
    :members:
    :undoc-members:
    :show-inheritance:

Bias Configuration
------------------

The class :class:`striptease.biases.InstrumentBiases` loads a set of biases for
each polarimeter and allows to query the biases for one polarimeter at time::

    import striptease
    biases = striptease.InstrumentBiases()

    # Query using the module name
    print(biases.get_biases("I0"))

    # Query using the polarimeter name
    print(biases.get_biases("STRIP58"))

.. automodule:: striptease.biases
    :members:
    :undoc-members:
    :show-inheritance:

Calibration
-----------

.. automodule:: calibration
    :members:
    :undoc-members:
    :show-inheritance:
       
Configuration
-------------

.. automodule:: config
    :members:
    :undoc-members:
    :show-inheritance:
