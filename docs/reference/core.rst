Core / Framework
================

Interactive model selection via tkinter.

.. dropdown:: Interactive Model Selection (GUI)

    .. automodule:: oemof.eesyplan.gui
        :members:
        :undoc-members:
        :show-inheritance:


Calculation of the capital recovery factor (CRF) and annuities for investment decisions.

.. autosummary::
    :nosignatures:

    ~oemof.eesyplan.investment.calculate_annuity
    ~oemof.eesyplan.investment.crf

.. dropdown:: Investment Appraisal (CRF & Annuity)

    .. automodule:: oemof.eesyplan.investment
        :members:
        :undoc-members:
        :show-inheritance:


Helper functions for unpacking datapackages.

.. dropdown:: Datapackage Extraction

    .. automodule:: oemof.eesyplan.io
        :members:
        :undoc-members:
        :show-inheritance:


Central energy system class, including optimisation and the results object.

.. autosummary::
    :nosignatures:

    ~oemof.eesyplan.model.EnergySystem
    ~oemof.eesyplan.model.Results
    ~oemof.eesyplan.model.optimise

.. dropdown:: Energy System & Optimisation

    .. automodule:: oemof.eesyplan.model
        :members:
        :undoc-members:
        :show-inheritance:


Economic framework of a project (interest rate, lifetime, investment logic).

.. dropdown:: Project Framework

    .. automodule:: oemof.eesyplan.project
        :members:
        :undoc-members:
        :show-inheritance:


Validation of input parameters.

.. dropdown:: Parameter Validation

    .. automodule:: oemof.eesyplan.type_checks
        :members:
        :undoc-members:
        :show-inheritance:


Mapping of datapackage identifiers to the corresponding component classes.

.. dropdown:: Type Mapping (TYPEMAP)

    .. automodule:: oemof.eesyplan.typemap
        :members:
        :undoc-members:
        :show-inheritance:
