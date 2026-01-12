.. _Introduction:

==============
Introduction
==============

This verification workflow originated from the METplus verification capabilities built into the `UFS Short-Range Weather (SRW) Application <https://ufs-srweather-app.readthedocs.io/en/latest/>`_. It is intended to replace the existing SRW verification capability make it more flexible, not only providing verification for SRW model output but also for other regional, global, and specialized (e.g. HAFS) applications.

.. _ug-organization:

User's Guide Organization 
============================

This documentation is organized into four sections: (1) *Background Information*; (2) *Setup, Running, and Testing the Workflow*; (3) *Customizing the Workflow*; and (4) *Reference*.

Background Information
-------------------------

   * This **Introduction** section explains how this documentation is organized, how to use this guide, and where to find user support and component documentation.
   * :numref:`Section %s: Technical Overview <TechOverview>` provides technical information about the verification workflow, including prerequisites and an overview of the code directory structure.
   * :numref:`Section %s: Workflow Components <Components>` provides a description of the application components, including optional components.

Setup, Running, and Testing the workflow
--------------------------------------------

   * :numref:`Section %s: Quick Start Guide <Quickstart>` is an overview of the workflow and gives instructions for its use
   * :numref:`Section %s: Prerequisites and Setup <Setup>` provides a *detailed* explanation of how to set up the verification workflow
   * :numref:`Section %s: Running the Verification Workflow <RunVX>` provides a *detailed* explanation of how to run the workflow after the prerequisites have been set up. It includes information on setting up particular verification tasks for different types of forecast and observation data, as well as techniques to run the workflow.
   * :numref:`Section %s: Testing the Verification Workflow <Testing>` explains how to run workflow end-to-end (WE2E) tests, continuous integration (CI) tests, and eventually regression tests (not yet implemented).
   * :numref:`Section %s: Tutorials <Tutorial>` walks users through a staged SRW App experiment cases with verification.
   * :numref:`Section %s: METplus Verification Sample Cases <VXCases>` explains how to run METplus verification as part of the workflow. 

.. hint:: 
   To get started with the Verification Workflow, it is recommended that users try one of the following options: 

    #. View :numref:`Section %s: Quick Start Guide <Quickstart>` for a quick overview of the workflow steps.
    #. For detailed instructions on prerequisites and setup, users can refer to :numref:`Section %s: Prerequisites and Setup <Setup>` and :numref:`Section %s: Running the Verification Workflow <RunVX>`.

Customizing the Workflow
---------------------------

   * :numref:`Section %s: Workflow Parameters <ConfigWorkflow>` documents all of the user-configurable experiment parameters that can be set in the user configuration file (``config.yaml``). 
   * :numref:`Section %s: Input & Output Files <InputOutputFiles>` describes application input and output files, as well as information on where to get publicly available data. 
   * :numref:`Section %s: Defining a Workflow <DefineWorkflow>` explains how to build a customized verification workflow XML file. 
   * :numref:`Section %s: Template Variables <TemplateVars>` explains how to use template variables. 

Reference Information
-----------------------

   * :numref:`Section %s: Rocoto Introductory Information <RocotoInfo>` provides an introduction to standard Rocoto (workflow manager) commands with examples.  
   * :numref:`Section %s: FAQ <FAQ>` answers users' frequently asked questions. 
   * :numref:`Section %s: Glossary <Glossary>` defines important terms related to MET, METplus, and the verification workflow. 

.. _doc-conventions:

Documentation Conventions
===================================

This guide uses particular conventions to indicate commands and code snippets, file and directory paths, variables, and options. 

.. code-block:: console

   Throughout the guide, this presentation style indicates shell commands, code snippets, etc.

Text rendered as ``AaBbCc123`` typically refers to variables in scripts, names of files, or directories.

Code that includes angle brackets (e.g., ``wflow_<platform>_<compiler>``) indicates that users should insert options appropriate to their configuration (e.g., ``wflow_hera_intel``). 

File or directory paths that begin with ``/path/to/`` should be replaced with the actual path on the user's system. For example, ``/path/to/ush`` might be replaced by ``/Users/Jane.Smith/dtc-vx-workflow/ush``. 

.. _component-docs:

Component Documentation
=========================

A list of available component documentation is shown in :numref:`Table %s <list_of_documentation>`. In general, technical documentation will explain how to use a particular component, whereas scientific documentation provides more in-depth information on the science involved in specific component files. 

.. _list_of_documentation:

.. list-table:: Centralized List of Documentation
   :widths: 20 50
   :header-rows: 1

   * - Documentation
     - Location
   * - Unified Workflow User's Guide
     - https://uwtools.readthedocs.io/en/stable/
   * - MET User's Guide
     - https://metplus.readthedocs.io/projects/met/en/latest/Users_Guide/
   * - METplus User's Guide
     - https://metplus.readthedocs.io/en/latest/Users_Guide/index.html


.. _user-support:

User Support and Contributions to Development
================================================

Questions
-----------

The workflow repository's `GitHub Discussions <https://github.com/dtcenter/dtc-vx-workflow/discussions>`__ forum provides a place to discuss with workflow developers, post questions, and exchange information. This Verification Workflow does not have any funding for public support, but questions will be answered if possible.


.. bibliography:: ../../references.bib
