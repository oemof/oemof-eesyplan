
Changelog
=========

0.0.1 (tba)
-----------

Added
-----

* **Auxiliary Heater**: Can use auxiliary energy to raise the temperature of
  heat flows from low-temperature components. For example, an unpressurised
  thermal store limited to 90–95 °C can supply a network requiring flow
  temperatures above 95 °C
  [:code:`components/converters/auxiliary_heat.py`}

* **Demand**: A generic demand component has been introduced as the basis for
  specialised demand components, such as electricity demand and heat demand.
  This simplifies maintenance. [:code:`components/demand/demand.py`]

* **Sink**: A Sink component is now available for expert users who need to
  create more complex model representations.
  [:code:`components/demand/sink.py`]

* **Commodity**: A new component for representing arbitrary resources, such as
  available waste or biomass.
  [:code:`components/production/commodity.py`]

* **Supplier**: A generic supplier component has been introduced, simplifying
  maintenance of supplier components and their specialised variants, such as
  electricity and heat suppliers. [:code:`components/providers/dso.py`]

* **Energy Storage**: A generic storage component has been added. Its
  parameter names have been aligned with those used for Supplier and Demand
  components. [:code:`components/storages/storage.py`]

* **Heating pipe**: Connects a heat source to a heating network or joins two
  sections of a heating network. It can be configured as unidirectional or
  bidirectional. [:code:`components/transport/heat.py`]

* **Heat Network**: The simplest heat-network configuration is now a Balance
  Node with multiple inputs (feed-ins) and outputs (consumers). The component
  can also account for heat losses.
  [:code:`components/transport/heat.py`]

* Importer added....

Changed
-------

* **Balance Node**: Can now include balancing components for surpluses and
  deficits directly. This allows models to run and produce results even where
  balances are incorrect, making balance errors easier to identify.
  [:code:`components/buses/carrier.py`]

* **Extraction Turbine**: Suitable for larger CHP plants, such as
  energy-from-waste facilities, as well as other CHP systems with a variable
  electricity-to-heat ratio. It is now defined solely by two operating
  points—maximum electricity output and maximum heat output—rather than by a
  power-loss coefficient.
  [:code:`components/converters/chp_variable_ratio.py`]

* **Heat Pump**: When using COP calculation in the importer, heat pumps can
  now be defined with one electricity input and one heat output. The air heat
  source is represented solely through the COP and no longer requires a
  separate ambient heat flow.
  [:code:`components/converters/heat_pump.py`]

* **Thermal Storage**: Loss parameters have been reorganised and tailored to
  thermal storage. [:code:`components/storages/thermal_storage.py`]

0.0.0 (2025-08-22)
------------------

* First release on PyPI.
