Importer
========

Calculation of the coefficient of performance (COP) of heat pumps, either
simplified or via TESPy.

COP calculation
----------------

Calculate the performance factor using the temperature of the source and the
supply temperature.

.. dropdown:: COP Calculation

    .. automodule:: oemof.eesyplan.importer.cop
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


.. dropdown:: Time Series Generation

    .. automodule:: oemof.eesyplan.importer.create_timeseries
        :members:
        :undoc-members:
        :show-inheritance:


Feed-in profiles
-----------------

Generation of PV or wind feed-in time series (currently inactive, based on
pvlib and windpowerlib).

.. dropdown:: PV Time Series (pvlib)

    .. automodule:: oemof.eesyplan.importer.create_timeseries_pv
        :members:
        :undoc-members:
        :show-inheritance:


Weather data
-------------

Reading and processing of DWD test reference year weather data.

.. dropdown:: Weather Data (DWD TRY)

    .. automodule:: oemof.eesyplan.weather.weather_data
        :members:
        :undoc-members:
        :show-inheritance:
