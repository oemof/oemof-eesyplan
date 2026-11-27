Preliminary calculations
========================

The following functions calculate input parameters for component classes using readily available data, such as weather data. They generate more complex inputs, including consumption profiles, feed-in time series and coefficient of performance (COP) time series.

Auxiliary heat calculation
--------------------------



.. dropdown:: Auxiliary heat calculation

    .. automodule:: oemof.eesyplan.importer.auxiliary_heat_fraction
        :members:
        :undoc-members:
        :show-inheritance:


COP calculation
---------------

Calculate the performance factor using the temperature of the source and the
supply temperature.

.. dropdown:: COP Calculation

    .. automodule:: oemof.eesyplan.importer.cop
        :members:
        :undoc-members:
        :show-inheritance:


Feed-in profiles
----------------

Generation of PV and Wind energy feed-in time serie, based on pvlib and windpowerlib.

.. dropdown:: PV Time Series (pvlib)

    .. automodule:: oemof.eesyplan.importer.create_timeseries_pv
        :members:
        :undoc-members:
        :show-inheritance:


Load profiles
-------------

Generation of time series for load profiles. Creation of heat load profiles
based on BDEW standard load profiles.

.. dropdown:: Heat Load Profiles (BDEW)

    .. automodule:: oemof.eesyplan.importer.heat_demand
        :members:
        :undoc-members:
        :show-inheritance:


Weather data
------------

Reading and processing of DWD test reference year weather data.

.. dropdown:: Weather Data (DWD TRY)

    .. automodule:: oemof.eesyplan.weather.weather_data
        :members:
        :undoc-members:
        :show-inheritance:
