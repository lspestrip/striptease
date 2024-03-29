Installation
============

Requirements
------------

To install Striptease, you need the following tools:

- Python 3.6 or later (required)
- A C++ compiler (optional, see below)

Installing the code
-------------------

To build the program, you must have the command ``git`` installed and
working on your computer.

Creating a new virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You are advised to create a new virtual environment for your work on
Striptease; this usually requires the following steps:

.. code-block:: sh

    python -m venv my_virtual_environment
    ?ACTIVATE?

where ``?ACTIVATE?`` is some command that depends on the platform
(Windows, Mac OS X, Linux) and shell (Bash, Zsh, Fish…) that you are
using. For instance, if you are using Bash/Zsh under Mac OS X or Linux,
you must run these commands:

.. code-block:: sh

    python -m venv my_virtual_environment
    source my_virtual_environment/bin/activate

If you are running the Command Prompt under Windows, the commands are
the following:

.. code-block:: text

    python -m venv my_virtual_environment
    my_virtual_environment\scripts\activate.bat

Refer to the `Python documentation
<https://docs.python.org/3/tutorial/venv.html>`_ for more details.


Downloading Striptease
~~~~~~~~~~~~~~~~~~~~~~

To install Striptease and its dependencies, use the following
commands:

.. code-block:: sh

    git clone git@github.com:lspestrip/striptease.git
    cd striptease
    pip install --user -r requirements.txt

Be sure to run your source codes and Jupyter notebooks within the
``striptease`` directory, otherwise calibration tables and other
important data files won't be visible.

However, if you need to access the instrument in real-time, you must
first set up the authentication system. To learn how to do it,
continue reading, otherwise you can stop here.


C++ GUI
-------

Striptease included a C++ program used to send long sequence of
commands to the Strip electronics. This program is no longer
supported, as the script `program_batch_runner.py` is now the
officially-supported way of running automatic scripts.

If you are curious and want to compile it, you must have a C++
compiler and the `Qt libraries <https://www.qt.io/>`_ installed. Run
the following commands within the ``striptease`` directory:

.. code-block:: bash

    cd TestRunner
    qmake TestRunner.pro && make


Authentication
--------------

To use the online tools provided by Striptease, you must have an
account for the STRIP web portal. (This is not necessary if you just
plan to load data from HDF5 files.) Once you are registered, you must
use your username and password to authenticate to the portal.

Striptease provides a number of shortcuts to provide your own
credentials to the web portal. Here are the possibilities:

1. Save your credentials in a text file, which is read any time
   Stripeline needs authentication. This requires some setup, but it's
   the best method.

2. Enter username and password every time. This is boring, but it's
   the most secure way to authenticate.

3. Use environment variables. This is unsecure, but quick to do.


Using credentials from a text file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We discuss this method first, because it is the most useful and
provides a secure yet permanent way to connect to the server without
re-entering your credentials again and again.

You must save your credentials in a JSON file named ``conf.json`` and
place it in the directory ``~/.strip``. Here is an example::

  {
    "user": "foo",
    "password": "bar"
  }

You can create this file from the command line, using the following
commands (on Mac OS X and Linux)::

  $ mkdir -p ~/.strip && cat <<EOF > ~/.strip/conf.json
  {
    "user": "foo",
    "password": "bar"
  }
  EOF

In order to secure your credentials, you should change the permission
of the directory ``.strip``::

  $ chmod -R go-rwx ~/.strip

Using environment variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A quick method to save your username and password is to use
environment variables. Striptease recognizes the variables
``STRIP_USER`` and ``STRIP_PASSWORD``, which you can set using the
following commands from terminal::

  $ export STRIP_USER=foo
  $ export STRIP_PASSWORD=bar

These variables will be lost once you close the terminal window. You
can make them permanent by adding the two ``export`` commands to your
``~/.profile`` file, but you should instead prefer to save them in
``conf.json`` (see above), as environment variables can be easily
tracked by other malicious users on your system.



Fast connection to the server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are working on the same computer where the data server is running,
you can save precious time when sending commands to it by skipping the
HTTP authentication stage. As this needs to be done for each command sent to
the server, skipping this part can lead to a significant boost in speed.

You must define the following new fields in the same file ``~/.strip/conf.json``
that was mentioned above:

- ``direct_server``: the name/IP of the machine running the data server
- ``direct_port``: the port used by the data server
- ``direct_user``: the username

So, the ``conf.json`` configuration file that was shown above should become
something like this::

  {
    "user": "foo",
    "password": "bar",
    "direct_server": "my_data_server",
    "direct_port": 12345,
    "direct_user": "john.smith"
  }

If there is any problem connecting to the data server with these credentials,
Striptease will emit a warning and fall back to the slower HTTP connection.
