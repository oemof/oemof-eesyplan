Components
==========

This page describes all solph-related building blocks, organised by category.

Buses
-----

Buses connect components within a single energy carrier (e.g. electricity, heat, gas).

.. dropdown:: Carrier Bus

    .. automodule:: oemof.eesyplan.components.buses.carrier
        :members:
        :undoc-members:
        :show-inheritance:


Compansation
------------

Balancing elements for energy excess and energy shortage.

.. dropdown:: Excess (Energy Surplus)

    .. automodule:: oemof.eesyplan.components.compansation.excess
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Shortage (Energy Deficit)

    .. automodule:: oemof.eesyplan.components.compansation.shortage
        :members:
        :undoc-members:
        :show-inheritance:


Converters
----------

Converters between energy carriers, e.g. boilers, heat pumps, electrolysers and CHP units.

.. dropdown:: Auxiliary Heat

    .. automodule:: oemof.eesyplan.components.converters.auxiliary_heat
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Boiler

    .. automodule:: oemof.eesyplan.components.converters.boiler
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: CHP (Fixed Ratio)

    .. automodule:: oemof.eesyplan.components.converters.chp_fixed_ratio
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: CHP (Variable Ratio)

    .. automodule:: oemof.eesyplan.components.converters.chp_variable_ratio
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Diesel Generator

    .. automodule:: oemof.eesyplan.components.converters.diesel_generator
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Electrical Transformer

    .. automodule:: oemof.eesyplan.components.converters.electrical_transformator
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Electrolyser

    .. automodule:: oemof.eesyplan.components.converters.electrolyzer
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Fuel Cell

    .. automodule:: oemof.eesyplan.components.converters.fuel_cell
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Heat Pump

    .. automodule:: oemof.eesyplan.components.converters.heat_pump
        :members:
        :undoc-members:
        :show-inheritance:


Demand
------

Demand-side components for electricity, heat, fuel and hydrogen requirements.

.. dropdown:: Demand (Base Class)

    .. automodule:: oemof.eesyplan.components.demand.demand
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Electricity Demand

    .. automodule:: oemof.eesyplan.components.demand.electricity_demand
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Fuel Demand

    .. automodule:: oemof.eesyplan.components.demand.fuel_demand
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Heat Demand

    .. automodule:: oemof.eesyplan.components.demand.heat_demand
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Hydrogen Demand

    .. automodule:: oemof.eesyplan.components.demand.hydrogen_demand
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Sink

    .. automodule:: oemof.eesyplan.components.demand.sink
        :members:
        :undoc-members:
        :show-inheritance:


Production
----------

Generation components such as PV, wind, biogas and geothermal plants.

.. dropdown:: Biogas Plant

    .. automodule:: oemof.eesyplan.components.production.biogas_plant
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Commodity

    .. automodule:: oemof.eesyplan.components.production.commodity
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Geothermal Plant

    .. automodule:: oemof.eesyplan.components.production.geothermal_plant
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: PV Plant

    .. automodule:: oemof.eesyplan.components.production.pv_plant
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Solar Thermal Plant

    .. automodule:: oemof.eesyplan.components.production.solar_thermal_plant
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Wind Turbine

    .. automodule:: oemof.eesyplan.components.production.wind_turbine
        :members:
        :undoc-members:
        :show-inheritance:


Providers
---------

Connection to upstream supply networks (DSO) for electricity, gas, heat and hydrogen.

.. dropdown:: DSO (Base Class)

    .. automodule:: oemof.eesyplan.components.providers.dso
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: DSO Electricity

    .. automodule:: oemof.eesyplan.components.providers.dso_electricity
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: DSO Fuel

    .. automodule:: oemof.eesyplan.components.providers.dso_fuel
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: DSO Heat

    .. automodule:: oemof.eesyplan.components.providers.dso_heat
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: DSO Hydrogen

    .. automodule:: oemof.eesyplan.components.providers.dso_hydrogen
        :members:
        :undoc-members:
        :show-inheritance:


Storages
--------

Storage components for electrical, thermal, fuel and hydrogen energy.

.. dropdown:: Electrical Storage

    .. automodule:: oemof.eesyplan.components.storages.electrical_storage
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Fuel Storage

    .. automodule:: oemof.eesyplan.components.storages.fuel_storage
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Hydrogen Storage

    .. automodule:: oemof.eesyplan.components.storages.hydrogen_storage
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Energy Storage (Base Class)

    .. automodule:: oemof.eesyplan.components.storages.storage
        :members:
        :undoc-members:
        :show-inheritance:


.. dropdown:: Thermal Storage

    .. automodule:: oemof.eesyplan.components.storages.thermal_storage
        :members:
        :undoc-members:
        :show-inheritance:
