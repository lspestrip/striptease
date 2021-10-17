Authentication
==============

In order to use the tools provided by Striptease, you must have an
account for the STRIP web portal. Once you are registered, you must
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
----------------------------------

We discuss this method first, because it is the most useful. You must
save your credentials in a JSON file named ``conf.json`` and place it
in the directory ``~/.strip``. Here is an example::

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
---------------------------

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
