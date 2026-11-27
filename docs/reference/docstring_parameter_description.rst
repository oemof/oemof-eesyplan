.. |absolute_losses| replace:: Absolute heat losses of the device per
    timestep [:unit:] (Acceptable values are either a non-negative real
    number or None).

.. |age_installed| replace:: Number of years the asset has already been
    in operation. If the project lasts longer than the asset's remaining
    lifetime, the replacement costs of the asset will be taken into
    account [a] (Natural number).

.. |air_pressure_hpa| replace:: Air pressure at station height [hPa]
    (pd.Series or None).

.. |air_temperature_c| replace:: Air temperature at 2 m above ground [°C]
    (pd.Series or None).

.. |albedo| replace:: Reflection fraction of sunlight in the surrounding
    area (numeric, default: 0.25).

.. |annual_fix_cost| replace:: Fixed annual cost of the asset that is
    independent of its capacity, used in postprocessing only.
    (non-negative real number).

.. |annual_heat_demand| replace:: Total heat demand in the chosen time
    period (numeric).

.. |atmospheric_radiation_wm2| replace:: Atmospheric longwave radiation on
    the horizontal plane [W/m²]. Positive means downward (pd.Series or None).

.. |auxiliary_heat_fraction| replace:: Share of the heat output that has
    to be provided by the auxiliary heat input in order to raise the heat
    flow to the supply temperature. [-] (real number between 0 and 1).

.. |azimuth| replace:: For fixed tilt: azimuth angle of the module
    orientation in degrees (North is 0°, East is 90°). For a tracker:
    azimuth angle of the rotation axis (numeric).

.. |balanced| replace:: Choose whether the sum of all inflows into the
    bus must equal the sum of all outflows at every timestep (energy
    balance constraint) [-] (acceptable values are either True or
    False).

.. |basic_amount| replace:: Fixed cost charged independently of the energy
    exchanged with the grid.

.. |building_year| replace:: Building year, used only for residential
    buildings to estimate insulation (int).

.. |bus| replace:: Connected Bus component through which energy is
    exchanged with the utility grid (DSO). [object].

.. |bus_1_heat| replace:: Connected Bus component for the first heat
    connection of the pipe. [object].

.. |bus_2_heat| replace:: Connected Bus component for the second heat
    connection of the pipe. [object].

.. |bus_in| replace:: Connected Bus component for an input flow. [object].

.. |bus_in_electricity| replace:: Connected Bus component for the electricity
    input flow. [object].

.. |bus_in_fuel| replace:: Connected Bus component for the fuel input flow.
    [object].

.. |bus_in_heat| replace:: Connected Bus component for the heat input flow.
    [object].

.. |bus_in_heat_auxiliary| replace:: Connected Bus component for the
    auxiliary heat input flow. [object].

.. |bus_in_hydrogen| replace:: Connected Bus component for the hydrogen input
    flow. [object].

.. |bus_out| replace:: Connected Bus component for the output flow. [object].

.. |bus_out_electricity| replace:: Connected Bus component for the electricity
    output flow. [object].

.. |bus_out_fuel| replace:: Connected Bus component for the fuel output flow.
    [object].

.. |bus_out_heat| replace:: Connected Bus component for the heat output flow.
    [object].

.. |bus_out_hydrogen| replace:: Connected Bus component for the hydrogen
    output flow. [object].

.. |c_rate_charge| replace:: Maximum charging power of the storage relative
    to its nominal storage capacity, e.g. 0.5 for a storage that needs two
    hours to charge completely [1/h] (acceptable values are either a
    positive real number or None).

.. |c_rate_discharge| replace:: Maximum discharging power of the storage
    relative to its nominal storage capacity, e.g. 1.0 for a storage that
    can be emptied within one hour [1/h] (acceptable values are either a
    positive real number or None).

.. |capacity| replace:: Nominal capacity of the component [:unit:]
    (non-negative real number).

.. |capex_spec| replace:: Specific investment costs of the asset related to
    the installed capacity (CAPEX) in €/:unit:.

.. |carrier| replace:: Energy carrier/medium, such as 'electricity', 'gas',
    'heat' or 'hydrogen' [-] (string).

.. |cloud_cover_oktas| replace:: Cloud cover [oktas]. Valid range: 0–8;
    9 means sky obscured (pd.Series or None).

.. |commodity| replace:: Commodity or energy carrier provided by the
    component. [-] (string).

.. |cop| replace:: Coefficient of performance. Ratio of energy output to
    energy input.

.. |cost_limited| replace:: TEXT MISSING

.. |cost_unlimited| replace:: TEXT MISSING

.. |custom_properties| replace:: Additional custom properties attached to the
    component. [-] (dict or None).

.. |custom_properties_flow| replace:: Additional custom properties attached
    to the flow definition of the component. [-] (dict or None).

.. |diffuse_irradiation_horizontal| replace:: Diffuse solar radiation on
    the horizontal plane [W/m²] (array-like with hourly timestep).

.. |diffuse_solar_wm2| replace:: Diffuse solar irradiance on the horizontal
    plane [W/m²]. Positive means downward (pd.Series or None).

.. |direct_irradiation_horizontal| replace:: Direct solar radiation on the
    horizontal plane [W/m²] (array-like with hourly timestep).

.. |direct_solar_wm2| replace:: Direct solar irradiance on the horizontal
    plane [W/m²]. Positive means downward (pd.Series or None).

.. |efficiency| replace:: Ratio of the energy delivered at the output of
    the component to the energy drawn at its input. The remaining share is
    accounted for as conversion losses. [-] (real number between 0 and 1).

.. |efficiency_charge| replace:: Conversion factor applied to the flow
    when charging the storage (inflow conversion factor), i.e. the
    share of the incoming energy that actually increases the storage
    content. [-] (real number between 0 and 1).

.. |efficiency_discharge| replace:: Conversion factor applied to the
    flow when discharging the storage (outflow conversion factor),
    i.e. the share of the storage content converted into usable
    outflow. [-] (real number between 0 and 1).

.. |efficiency_electricity_chp| replace:: Electrical efficiency with maximal
    heat extraction [-] (real number between 0 and 1).

.. |efficiency_electricity_state_a| replace:: Electrical efficiency of
    the CHP at operating state a (full condensation operation), i.e.
    the conversion ratio from fuel to electricity when no heat is
    extracted [-] (real number between 0 and 1).

.. |efficiency_electricity_state_b| replace:: Electrical efficiency of
    the CHP at operating state b (maximal heat extraction operation),
    i.e. the conversion ratio from fuel to electricity when heat
    extraction is at its maximum [-] (real number between 0 and 1).

.. |efficiency_heat| replace:: Ratio of waste heat recovered to
    electricity consumed by the electrolyzer [-] (real number between
    0 and 1).

.. |efficiency_heat_chp| replace:: Thermal efficiency with maximal heat
    extraction [-] (real number between 0 and 1).

.. |efficiency_heat_state_a| replace:: Thermal efficiency of the CHP at
    operating state a (full condensation operation) [-] (real number
    between 0 and 1).

.. |efficiency_heat_state_b| replace:: Thermal efficiency of the CHP at
    operating state b (maximal heat extraction operation) [-] (real
    number between 0 and 1).

.. |end_storage_level| replace:: Choose whether the storage content of the
    first and the last timestep of the optimisation horizon should be
    equal [-] (acceptable values are either True or False).

.. |energy_price| replace:: Price of the energy carrier sourced from the
    utility grid. May also be a time series, in €/kWh.

.. |eta_s| replace:: TEXT MISSING

.. |excess_cost| replace:: Cost incurred per unit of energy absorbed by
    the excess sink. Typically set to a high value to penalise and
    thus avoid excess energy in the optimisation results, unless
    deliberately used to model a cost-free energy outlet (e.g.
    curtailment) [currency/unit] (acceptable values are either a real
    number or a series of real numbers).

.. |feedin_cap| replace:: Maximum flow for feeding electricity into the grid
    at any given timestep, in kW (acceptable values are either a positive
    real number or None).

.. |feedin_tariff| replace:: Price received for feeding electricity into the
    grid. May also be a time series, in €/kWh.

.. |file| replace:: TEXT MISSING

.. |fix| replace:: Fixed operation profile of the flow. Can be given as a
    scalar or time series relative to the nominal capacity [-]
    (acceptable values are either a real number, an iterable, or None).

.. |fixed_losses_absolute| replace:: Losses of the storage between two
    consecutive timesteps that are independent of both the state of charge
    and the nominal storage capacity [:unit:] (non-negative real number).

.. |fixed_losses_relative| replace:: Losses of the storage between two
    consecutive timesteps that are independent of the state of charge,
    relative to the nominal storage capacity [-] (real number between 0
    and 1).

.. |full_load_time_limit| replace:: TEXT MISSING

.. |full_load_time_max| replace:: Maximum number of full load hours the
    asset may accumulate over the optimisation horizon, used e.g. to
    represent licensing or resource limits [h] (acceptable values are
    either a non-negative real number or None).

.. |full_load_time_min| replace:: Minimum number of full load hours the
    asset has to accumulate over the optimisation horizon, e.g. due to
    contractual take-or-pay obligations [h] (acceptable values are either
    a non-negative real number or None).

.. |gcr| replace:: Ground Coverage Ratio: ratio of the module area to the
    ground area of the module field. Only needed for trackers (numeric).

.. |initial_storage_level| replace:: Initial relative storage level at the
    first timestep, as a factor of the nominal storage capacity [-]
    (acceptable values are either a real number between 0 and 1, or None,
    in which case the level is determined freely by the optimisation).

.. |input_timeseries| replace:: Time series in :unit:.

.. |installed_capacity| replace:: Already existing installed capacity. If the
    project lasts longer than its remaining lifetime, the replacement costs
    of the asset will be taken into account, in :unit:.

.. |integer| replace:: Choose whether the investment decision variable of
    the asset should be restricted to integer values. [-] (acceptable
    values are either True or False).

.. |investment_fix_cost| replace:: Fixed investment cost of the asset
    that is independent of its capacity, used in postprocessing only.
    (non-negative real number).

.. |latitude| replace:: TEXT MISSING

.. |lifetime| replace:: Number of operational years of the asset before it
    has to be replaced [a] (natural number).

.. |longitude| replace:: TEXT MISSING

.. |loss_rate| replace:: Relative loss of the storage content between two
    consecutive timesteps, applied to the current state of charge [-]
    (real number between 0 and 1).

.. |max_angle| replace:: Maximum tilt angle for tracking systems. Only used
    for tracker systems (numeric, default: 60°).

.. |maximum| replace:: Maximum operation level of the flow as a factor of
    the nominal capacity [-] (acceptable values are either a real number
    between 0 and 1, or None).

.. |maximum_capacity| replace:: Maximum total capacity of an asset that can
    be installed at the project site. This includes the already existing
    installed capacity and the additional capacity possible. For example, a
    roof might only be able to carry 50 kW of PV (maximum capacity), whereas
    10 kW is already installed. The optimisation would then only be allowed
    to add 40 kW of PV at most, in :unit: (acceptable values are either a
    positive real number or None).

.. |maximum_feedin_capacity| replace:: Maximum capacity of the connection
    that may be used for feeding electricity into the grid. [kW]
    (acceptable values are either a non-negative real number or None).

.. |maximum_limited_path| replace:: TEXT MISSING

.. |maximum_unlimited_path| replace:: TEXT MISSING

.. |minimum| replace:: Minimum operation level of the flow as a factor of
    the nominal capacity [-] (acceptable values are either a real number
    between 0 and 1, or None).

.. |mounting_type| replace:: Mounting type (string): "fix tilt" for static
    systems with one orientation; "fix tilt two directions back to back"
    for an east-west-like system, where the second orientation is set up
    automatically; or "tracker" for one-axis tracking systems.

.. |name| replace:: Name of the asset. [-] (Input the name in a
    computer-friendly format, preferably with underscores instead of
    spaces, and avoiding special characters).

.. |negative_gradient_limit| replace:: Maximum allowed decrease of the flow
    between two consecutive timesteps as a factor of the nominal capacity
    [-] (acceptable values are either a non-negative real number or None).

.. |opex_spec| replace:: Specific operational and maintenance costs of the
    asset related to the installed capacity (opex_spec), in €/(:unit: • a).

.. |outdoor_temperature| replace:: Outside air temperature [°C] (numeric,
    scalar or iterable).

.. |peak_demand_pricing| replace:: Grid fee to be paid based on the peak
    demand of a given period, in €/kW.

.. |peak_demand_pricing_period| replace:: Number of reference periods in one year
    for peak demand pricing, in times per year (only the following values
    are acceptable: 1 (yearly), 2, 3, 4, 6, 12 (monthly)).

.. |positive_gradient_limit| replace:: Maximum allowed increase of the flow
    between two consecutive timesteps as a factor of the nominal capacity
    [-] (acceptable values are either a non-negative real number or None).

.. |pressure_loss_factor_hex| replace:: TEXT MISSING

.. |profile_type| replace:: BDEW heat profile (string). Available profiles:
    "EFH" or "Single-family house"; "MFH" or "Apartment building";
    "GHD" or "Commerce/Services general"; "GMF" or "Household-like
    business enterprises"; "GGA" or "Restaurants"; "GBH" or "Retail and
    wholesale"; "GMK" or "Metal and automotive"; "GBH" or
    "Accommodation"; "GKO" or "Local authorities, credit institutions and
    insurance companies"; "GBD" or "Other operational services"; "GWA" or
    "Laundries, dry cleaning"; "GGB" or "Horticulture"; "GBA" or "Bakery";
    "GPD" or "Paper and printing".

.. |project_data| replace:: The framework of the project in which the asset
    is to be optimised.

.. |quality_factor| replace:: TEXT MISSING

.. |quality_flag| replace:: Quality flag regarding selection criteria
    (pd.Series or None).

.. |refrigerant| replace:: TEXT MISSING

.. |relative_humidity_percent| replace:: Relative humidity at 2 m above
    ground [%]. Valid range: 1–100 (pd.Series or None).

.. |relative_losses| replace:: Relative heat losses of the pipe per
    timestep as a factor of the transferred heat [-] (acceptable values
    are either a real number between 0 and 1).

.. |renewable_asset| replace:: Choose whether this asset should be
    considered renewable. This parameter is necessary to consider the
    renewable share constraint correctly. [-] (acceptable values are either
    Yes or No).

.. |renewable_share| replace:: Share of renewables in the generation mix of
    the energy supplied by the DSO utility. [Factor] (real number between 0
    and 1).

.. |return_pipe| replace:: Specifies whether the return pipe is included
    in the representation of the heating pipe [-] (acceptable values are
    either Yes or No).

.. |shortage_cost| replace:: Cost incurred per unit of energy supplied
    by the shortage source to cover an otherwise infeasible energy
    deficit. Typically set to a high value to penalise and thus avoid
    shortage energy in the optimisation results [currency/unit]
    (acceptable values are either a real number or a series of real
    numbers).

.. |soc_max| replace:: The maximum permissible level of charge of the storage
    as a factor of the nominal capacity. When the battery is filled to its
    nominal capacity, the state of charge is represented by the value 1 [-]
    (real number between 0 and 1).

.. |soc_min| replace:: The minimum permissible level of charge of the storage
    as a factor of the nominal capacity. When the battery is fully
    discharged, the state of charge is represented by the value 0 [-] (real
    number between 0 and 1).

.. |start_datetime| replace:: Timestamp in datetime format (str, default:
    "2021-01-01 0:00").

.. |system_eff| replace:: Performance ratio of the total PV system, usually
    around 0.8 (numeric).

.. |temp_in_heat| replace:: Temperature of the incoming heat flow
    [°C] (real number above 0).

.. |temp_low_source_component| replace:: The return flow temperature of the
    upstream component. If the upstream component is, for example, a storage
    tank, this refers to the cold temperature of the tank. In the case of a
    heat pump, it would be the temperature of the incoming water (not the
    temperature of the heat source). [°C] (real number above 0).

.. |temp_out_heat| replace:: Temperature of the outgoing heat flow. Note
    that the temperature of the auxiliary heat is assumed to be above this
    temperature. [°C] (real number above 0).

.. |temperature_aux| replace:: TEXT MISSING

.. |temperature_difference_aux| replace:: TEXT MISSING

.. |temperature_difference_source| replace:: TEXT MISSING

.. |temperature_source| replace:: TEXT MISSING

.. |temperature_supply| replace:: TEXT MISSING

.. |terrestrial_radiation_wm2| replace:: Terrestrial longwave radiation
    [W/m²]. Negative means upward (pd.Series or None).

.. |tilt| replace:: Tilt angle in degrees: 0° is horizontal and 90° is
    vertical (numeric).

.. |tz| replace:: Timezone in datetime format (str, default:
    "Europe/Berlin").

.. |value| replace:: No TEXT

.. |variable_costs| replace:: Costs associated with a flow through or out of
    the asset, e.g. fuel costs for sources such as biogas or oil, or
    operation-dependent costs of a thermal power plant [€/kWh] (acceptable
    values are either a non-negative real number or a series of
    non-negative real numbers).

.. |virtual_flow_capacity| replace:: TEXT MISSING

.. |water_vapor_gkg| replace:: Water vapor content, mixing ratio [g/kg]
    (pd.Series or None).

.. |wind_class| replace:: "Windy" for exposed buildings on free fields,
    near the coast or on high ground; "Not windy" for unexposed buildings
    in villages or cities (str).

.. |wind_direction_deg| replace:: Wind direction at 10 m above ground
    [degrees]. Valid range: 0–360; 999 means variable (pd.Series or None).

.. |wind_speed_ms| replace:: Wind speed at 10 m above ground [m/s]
    (pd.Series or None).
