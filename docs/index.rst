PyIPTV Documentation
====================

Welcome to PyIPTV's documentation! PyIPTV is a modern, feature-rich IPTV player built with PySide6/Qt6, designed for streaming live television content from M3U playlists.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   api
   development
   contributing

Features
--------

Core Functionality
~~~~~~~~~~~~~~~~~~

* 📺 **M3U Playlist Support** - Load and manage IPTV playlists in M3U format
* 🎨 **Modern Qt6 Interface** - Built with PySide6 for a responsive, native desktop experience
* 📂 **Category Organization** - Automatically organize channels by categories
* 🔍 **Search & Filtering** - Quickly find channels with real-time search
* 🎵 **Audio Track Selection** - Multi-language audio track support

User Experience
~~~~~~~~~~~~~~~

* 🌓 **Theme Support** - System-aware theming with KDE integration
* ⚡ **Performance Optimized** - Handles large playlists with virtualized lists and smart buffering
* ⚙️ **Settings Management** - Persistent settings with user-friendly configuration
* 🖥️ **High DPI Support** - Optimized for high-resolution displays

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install pyiptv

Basic Usage
~~~~~~~~~~~

Launch PyIPTV without arguments to open the playlist manager:

.. code-block:: bash

   pyiptv

Launch directly with a playlist file:

.. code-block:: bash

   pyiptv /path/to/your/playlist.m3u

Architecture Overview
--------------------

PyIPTV follows a modular architecture design:

.. code-block:: text

   ┌─────────────────┐
   │ Main Application│
   ├─────────────────┤
   │ UI Components   │
   │ Playlist Manager│
   │ Media Player    │
   │ Settings Manager│
   │ Theme Manager   │
   └─────────────────┘

Components
~~~~~~~~~~

* **Main Application** - Entry point and application lifecycle management
* **UI Components** - Modular Qt widgets for different functionality
* **Playlist Manager** - M3U parsing and playlist management
* **Media Player** - Qt6 multimedia integration
* **Settings Manager** - Configuration persistence
* **Theme Manager** - System-aware theming

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
