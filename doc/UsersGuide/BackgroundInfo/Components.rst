.. _Components:

================================
Verification Workflow Components
================================

The verification workflow assembles a variety of components, including:

* Unified Workflow Tools
* Model Evaluation Tools and METplus
* Rocoto workflow manager

These components are documented within this User's Guide and supported through the `GitHub Discussions <https://github.com/dtcenter/dtc-vx-workflow/discussions>`__ forum. 

.. _Utils:

METplus Verification Suite
=============================

The Model Evaluation Tools (MET) package is a set of statistical verification tools developed by the `Developmental Testbed Center <https://dtcenter.org/>`_ (DTC) for use by the :term:`NWP` community to help them assess and evaluate the performance of numerical weather predictions. MET is the core component of the enhanced `METplus <https://dtcenter.org/community-code/metplus>`_ verification framework; the suite also includes the associated database and display systems called METviewer and METexpress. 

The METplus verification framework has capabilities to verify forecasts that span a wide range of temporal scales (warn-on-forecast to climate) and spatial scales (storm to global). It is supported by the `Developmental Testbed Center (DTC) <https://dtcenter.org/>`_. 

METplus comes preinstalled with :term:`spack-stack`. Users on systems without a previous installation of METplus can follow the :ref:`MET Installation Guide <met:installation>` and :ref:`METplus Installation Guide <metplus:install>` for individual installation. For custom METplus installations, users will need to modify their config.yaml file to include the following settings under the ``platform:`` section:

.. code-block:: console

   MET_INSTALL_DIR: ''
   METPLUS_ROOT: ''


The core components of the METplus framework include the statistical driver (MET), the associated database and display systems known as METviewer and METexpress, and a suite of Python wrappers to provide low-level automation and examples, also called use cases. MET is a set of verification tools developed for use by the :term:`NWP` community. It matches up gridded forecast fields with either gridded analyses or point observations and applies configurable methods to compute statistics and diagnostics. Extensive documentation is available in the :doc:`METplus User's Guide <metplus:index>` and :doc:`MET User's Guide <met:index>`. Documentation for all other components of the framework can be found at the *Documentation* link for each component on the METplus `downloads <https://dtcenter.org/community-code/metplus/download>`_ page.

Among other techniques, MET provides the capability to compute standard verification scores for comparing deterministic gridded model data to point-based and gridded observations. It also provides ensemble and probabilistic verification methods for comparing gridded model data to point-based or gridded observations. Verification tasks to accomplish these comparisons are defined in the :numref:`Table %s <VXWorkflowTasksTable>`. Currently, the verification workflow supports the use of :term:`NDAS` observation files (which include conventional point-based surface and upper-air data) `in prepBUFR format <https://nomads.ncep.noaa.gov/pub/data/nccf/com/nam/prod/>`__ for point-based verification. It also supports gridded Climatology-Calibrated Precipitation Analysis (:term:`CCPA`) data for accumulated precipitation evaluation and Multi-Radar/Multi-Sensor (:term:`MRMS`) gridded analysis data for composite reflectivity and :term:`echo top` verification. 

METplus is being actively developed by :term:`NCAR`/Research Applications Laboratory (RAL), NOAA/Earth Systems Research Laboratories (`ESRL <https://www.esrl.noaa.gov/>`__), and NOAA/Environmental Modeling Center (:term:`EMC`), and it is open to community contributions. More details about METplus can be found on the `METplus website <https://dtcenter.org/community-code/metplus>`_.

.. _uwtools:

Unified Workflow Tools (``uwtools``)
======================================

``uwtools`` is a modern, open-source Python package that helps automate common tasks needed for many standard numerical weather prediction (NWP) workflows. It also provides drivers to automate the configuration and execution of UFS components, providing flexibility, interoperability, and usability to various UFS applications. The Unified Workflow (UW) tools are accessible from both a command-line interface (CLI) and a Python API. The CLI automates many core NWP workflow functions; the API supports all CLI operations and additionally provides access to in-memory objects to facilitate more novel use cases. These options allow users to integrate the package into pre-existing bash and Python scripts, in addition to providing some handy tools for use in day-to-day work with NWP systems. The ``uwtools`` template and configuration (config) tools have been incorporated into the verification workflow, being used to generate the Rocoto XML file for defining an experiment's workflow, as well as filling in METplus configuration file tempaltes. More details about UW tools can be found in the `uwtools GitHub repository <https://github.com/ufs-community/uwtools>`_ and in the :uw:`UW Documentation <>`.

Workflow
=========================

Once built, users can generate a Rocoto-based workflow that will run each task in the proper sequence (see :numref:`Chapter %s <RocotoInfo>` or the `Rocoto documentation <https://github.com/christopherwharrop/rocoto/wiki/Documentation>`__ for more information on Rocoto and workflow management). If Rocoto, METplus, or a batch system is not present on the platform, the workflow can not be run, though we plan to allow for arbitrary system installation in the future.

Users can various elements of the workflow by changing settings in the config.yaml file. For example, users can modify the dates and forecast hours to verify data, the specific verification tasks to run, and observation types to verify against. More information on how to configure the workflow is available in :numref:`Section %s <UserSpecificConfig>`.

The verification workflow has been tested on a variety of platforms widely used by researchers, including NOAA High-Performance Computing (HPC) systems (e.g., Hera, Gaea-C6); the National Center for Atmospheric Research (:term:`NCAR`) Derecho system; and MSU HPC systems (Orion and Hercules). Support for arbitrary UNIX and LINUX-based platforms is a future goal.

