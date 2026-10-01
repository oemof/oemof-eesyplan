Importer
========

Calculation of the coefficient of performance (COP) of heat pumps - either simplified or via TESPy.

.. autosummary::
    :nosignatures:

    ~oemof.eesyplan.importer.cop.calculate_cop_simple
    ~oemof.eesyplan.importer.cop.calculate_cop_tespy

.. dropdown:: COP Calculation

    .. automodule:: oemof.eesyplan.importer.cop
        :members:
        :undoc-members:
        :show-inheritance:


Generation of time series for load profiles.

.. dropdown:: Time Series Generation

    .. automodule:: oemof.eesyplan.importer.create_timeseries
        :members:
        :undoc-members:
        :show-inheritance:


Generation of PV feed-in time series (currently inactive, based on pvlib).

.. dropdown:: PV Time Series (pvlib)

    .. automodule:: oemof.eesyplan.importer.create_timeseries_pv
        :members:
        :undoc-members:
        :show-inheritance:


Creation of heat load profiles based on BDEW standard load profiles.

.. autosummary::
    :nosignatures:

    ~oemof.eesyplan.importer.heat_demand.create_heat_demand
    ~oemof.eesyplan.importer.heat_demand.import_heat_demand_f_heat

.. dropdown:: Heat Load Profiles (BDEW)

    .. automodule:: oemof.eesyplan.importer.heat_demand
        :members:
        :undoc-members:
        :show-inheritance:


Reading and processing of DWD test reference year weather data.

.. autosummary::
    :nosignatures:

    ~oemof.eesyplan.weather.weather_data.WeatherData
    ~oemof.eesyplan.weather.weather_data.lon_lat_from_lambert
    ~oemof.eesyplan.weather.weather_data.try_file2df

.. dropdown:: Weather Data (DWD TRY)

    .. automodule:: oemof.eesyplan.weather.weather_data
        :members:
        :undoc-members:
        :show-inheritance:
