.. _doc-guidelines:

Documentation
=============

.. note:: 
   
   Thank you to the Unified Workflow (UW) team for allowing us to adapt their documentation guidance for use in the SRW App. The original can be viewed in the `uwtools` :uw:`documentation <sections/contributor_guide/documentation.html>`.


Locally Building and Previewing Documentation
---------------------------------------------

To locally build the docs:

#. From the top-level directory of your clone, create (the first time) and activate the ``vx_docs`` conda environment, which has the packages needed to build the documentation (see :ref:`doc-dependencies`): ``source setup_conda.sh vx_docs``
#. ``cd doc``
#. Build the docs: ``make html``

The ``make html`` command builds the documentation under ``doc/build/html`` and writes any errors and warnings to ``doc/build/warnings.log``. The documentation can then be previewed in a web browser at the URL:

.. code-block:: text

   file://<filesystem-path-to-your-clone>/doc/build/html/index.html

Rerun ``make html`` and refresh your browser after making and saving changes. The ``make doc`` command does more: it first removes the previous build, then checks the links in the documentation (which needs internet access), then builds the HTML.

.. _doc-dependencies:

Documentation Dependencies
--------------------------

The Python packages needed to build the documentation are listed in two files in the ``doc`` directory:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - File
     - Written by
     - Contents and use
   * - ``requirements.in``
     - Developers
     - The packages that the documentation uses itself, i.e., Sphinx and the theme and extensions that ``doc/conf.py`` loads, with loose version limits (e.g., ``sphinx_rtd_theme>=3.0.0``). It is used only to regenerate ``requirements.txt``.
   * - ``requirements.txt``
     - ``pip-compile``
     - Every package needed, including those needed only by the packages in ``requirements.in`` (for each package, a ``# via`` comment says which package needs it), each pinned to an exact version (e.g., ``docutils==0.20.1``). Read the Docs (as set in ``.readthedocs.yaml`` in the top-level directory of the repo) and the ``vx_docs`` conda environment install from this file.

Both files are kept in the repository because each holds something the other doesn't:

* ``requirements.txt`` makes builds reproducible. If builds installed from ``requirements.in`` instead, each build would get the newest versions allowed on that day, so the documentation could change or fail to build without any change in the repository. With ``requirements.txt``, every build of a given commit uses the same versions, until someone deliberately regenerates the file.
* ``requirements.in`` records which packages the documentation actually needs, as opposed to those that are there only as dependencies of others, and makes upgrading easy: change it, then regenerate ``requirements.txt``, and ``pip-compile`` works out a consistent set of versions.

To change the packages or their versions, edit ``requirements.in``, not ``requirements.txt``: ``pip-compile`` overwrites ``requirements.txt``, so any change made to it by hand is lost the next time it is regenerated. Then regenerate ``requirements.txt`` by running the following from the ``doc`` directory, in an environment that has the ``pip-tools`` package installed:

.. code-block:: console

   pip-compile requirements.in

After regenerating ``requirements.txt`` from ``requirements.in``, include the two in the same commit so that they remain consistent.

Viewing Online Documentation
----------------------------

Online documentation generation and hosting for the SRW App is provided by :rtd:`Read the Docs<>`. The green *View Docs* button near the upper right of that page links to the official docs for the project. When viewing the documentation, the version selector at the bottom of the navigation column on the left can be used to switch between the latest development code (``develop``), the latest released version (``latest``), and any previously released version.

Docs are also built and temporarily published when Pull Requests (PRs) targeting the ``develop`` branch are opened. Visit the :rtd:`Builds page<builds>` to see recent builds, including those made for PRs. Click a PR-related build marked *Passed*, then the small *View docs* link (**not** the large green *View Docs* button) to see the docs built specifically for that PR. If your PR includes documentation updates, it may be helpful to include the URL of this build in your PR's description so that reviewers can see the rendered HTML docs and not just the modified ``.rst`` files. Note that if commits are pushed to the PR's source branch, Read the Docs will rebuild the PR docs. See the checks section near the bottom of a PR for current status and for another link to the PR docs via the *Details* link.

.. COMMENT: Technically, docs are built when any PR is opened, regardless of branch. Look into changing. 

Documentation Guidelines
------------------------

Please follow these guidelines when contributing to the documentation:

* Keep formatting consistent across pages. Update all pages when better ideas are discovered. Otherwise, follow the conventions established in existing content.
* Ensure that the ``make doc`` command completes with no errors or warnings.
* If the link-check portion of ``make doc`` reports that a URL is ``permanently`` redirected, update the link in the docs to use the new URL. Non-permanent redirects can be left as-is.
* Do not manually wrap lines in the ``.rst`` files. Insert newlines only as needed to achieve correctly formatted HTML, and let HTML wrap long lines and/or provide a scrollbar.
* Use one blank line between documentation elements (headers, paragraphs, code blocks, etc.) unless additional lines are necessary to achieve correctly formatted HTML.
* Remove all trailing whitespace.
* In general, avoid pronouns like "we" and "you". (Using "we" may be appropriate when synonymous with "The SRW Code Management Team", "The UFS Community", etc., when the context is clear.) Prefer direct, factual statements about what the code does, requires, etc.
* Use the `Oxford Comma <https://en.wikipedia.org/wiki/Serial_comma>`__.
* Follow the :rst:`RST Sections<basics.html#sections>` guidelines, underlining section headings with = characters, subsections with - characters, and subsubsections with ^ characters. If a further level of refinement is needed, use " to underline paragraph headers.
* In [[sub]sub]section titles, capitalize all "principal" words. In practice this usually means all words but articles (a, an, the), logicals (and, etc.), and prepositions (for, of, etc.). Always fully capitalize acronyms (e.g., YAML).
* Never capitalize proper names when their owners do not (e.g., write `"pandas" <https://pandas.pydata.org/>`__, not "Pandas", even at the start of a sentence) or when referring to a software artifact (e.g., write ``numpy`` when referring to the library, and "NumPy" when referring to the project).
* When referring to YAML constructs, ``block`` refers to an entry whose values is a nested collection of key/value pairs, while ``entry`` is a single key/value pair.
* When using the ``.. code-block::`` directive, align the actual code with the word ``code``. Also, when ``.. code-block::`` directives appear in bulleted or numberd lists, align them with the text following the space to the right of the bullet/number. Include a blank line prior to the coe content. For example:

  .. code-block:: text

     * Lorem ipsum

       .. code-block:: python

          n = 88

  or

  .. code-block:: text

     #. Lorem ipsum

        .. code-block:: python

           n = 88

Troubleshooting Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The documentation Makefile (``doc/Makefile``) runs Sphinx with the ``--keep-going`` option, so a build continues past errors and reports all errors and warnings, both on the screen and in ``doc/build/warnings.log``. A build with warnings still succeeds, so check that file for new warnings before opening a PR.

Technical Documentation Guidelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Technical (API-like) documentation is generated for any Python scripts in the ``ush`` or ``tests/WE2E`` directories. 
When developers change Python files in these directories, they need to update the Python docstrings (i.e., comments in ``"""triple quotes"""``) to reflect the changes they made. 
Each Python script should include: 

   * A summary of the script's purpose/functionality
      
      * Should start with a verb, e.g., "checks" or "loads" or "initializes"

   * Docstrings for each method (except methods like ``_parse_args`` that start with an underscore). These docstrings should include:

      * A description of what the method does (starting with a verb, e.g., "checks" or "parses")
      * A list of method parameters, or ``Args:``, with a definition and expected data type for each
      * A return statement (``Returns:``) -- if applicable
      * List of exceptions (``Raises:``) -- if applicable

.. note:: 
   
   Python does not have truly private methods, but methods that start with an underscore are the closest equivalent. In the SRW App, the underscore signals that this method is only accessed by the script within which it is called. 

After updating the docstrings, developers need to update the corresponding RST files. 
To do this successfully, developers need Sphinx 7.4.0 or later, for the ``--remove-old`` option used below; the ``vx_docs`` environment has a newer one (its exact version is in ``doc/requirements.txt``). To update the RST files, run the following from the top-level directory of your clone:

.. code-block:: console

   cd doc/TechDocs
   sphinx-apidoc -fM --remove-old -o ./ush ../../ush
   sphinx-apidoc -fM --remove-old -o ./tests/WE2E ../../tests/WE2E

.. note:: 

   Developers who do not have *sphinx>=7.4.0* installed may issue the following commands from ``doc/TechDocs`` before running the sphinx-apidoc commands above:

   .. code-block:: console

      rm -rf ush
      rm -rf tests/WE2E
   
   This will delete current RST files before recreating them with the ``sphinx-apidoc`` command based on the current contents of ``ush`` and ``tests/WE2E``. This step is necessary because the ``--remove-old`` flag does not work with earlier versions of sphinx. 
