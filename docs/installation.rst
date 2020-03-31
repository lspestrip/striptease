Installation
============

Requirements
------------

To install Striptease, you need the following tools:

- Python 3.6 or later (required)
- A C++ compiler (optional, see below)

Installing the code
-------------------

You have two choices to install this program:

1. Install and use it as any other Python package; good if you are not
   a Python expert but just want to control the Strip instrument;

2. Install it with the aim to develop and improve it; good if you know
   some Python and do not want to prevent yourself from patching the
   code.
   
If you want to follow the first route, use the following commands
(possibly after having `created a virtual environment
<https://docs.python.org/3/library/venv.html>`_):

.. code-block:: bash
                
    git clone git@github.com:lspestrip/striptease.git
    cd striptease
    python setup.py install

If you are a developer (point 2 above), use these commands:

.. code-block:: bash
                
    git clone git@github.com:lspestrip/striptease.git
    cd striptease
    python -m pip install -e .

Striptease includes a C++ program used to send long sequence of
commands to the Strip electronics. You do not need to compile this
code, if you do not have the rights to command the hardware. This
program is written in C++ and requires you have a C++ compiler. Run
the following commands within the ``striptease`` directory:

.. code-block:: bash
                
    cd TestRunner
    qmake TestRunner.pro && make

Once the code is installed, you can use it in IPython, Jupyter, or
Python scripts, using the following ``import``::

  import striptease

However, if you need to access the instrument in real-time, you must
first set up the authentication system. To learn how to do it,
continue reading, otherwise you can stop here.

  
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
