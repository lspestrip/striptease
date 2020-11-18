# How to contribute with some code

If you want to fix/add code to this repository, this is the approved
procedure:

-   If you do not have cloned this repository, do it immediately:

    ```
    git clone git@github.com:lspestrip/striptease.git
    cd striptease
    ```
    
-   You must now create a «branch», i.e., a copy of the code which is
    under your complete control, and name this branch aptly. Assume
    that the feature you're working on is a set of tools to compute
    spectra, you could name your branch `compute_spectra`. To create
    the branch, run this command:
    
    ```
    git checkout -b compute_spectra
    ```
    
    **Please use branches and pull requests, and resist the temptation
    to do commits to `master`, unless they are really trivial! The
    procedure outlined here has several benefits!**

-   Now feel free to change files, create new ones, and make commits.
    Please make as many commits as necessary: it's better to have many
    small commits than one huge commit!

-   Once you're ready to publish your work, you must create a «pull
    request». A Pull Request is a way to tell other people developing
    the code that you're suggesting a change, and that you want your
    collaborators to review it and give their opinions.
    
    The first step is to publish your branch, because so far it only
    lives in your computer: you must «push» the branch
    `compute_spectra` to GitHub, so that other people can see it. The
    following command forces GitHub (called `origin` in Git's slang)
    to create a branch on its servers with the name `compute_spectra`,
    and mirror your local copy of the branch to its own:
    
    ```
    git push --set-upstream origin compute_spectra
    ```
    
-   The command `git` will produce a message, saying that you must
    visit a specific URL to open a «pull request», which will probably
    be in the following form:
    
    https://github.com/lspestrip/striptease/pull/new/compute_spectra
    
    Open the URL displayed by `git` on the terminal and create the
    pull request. Use a short title to describe the content of the PR,
    and the «comment» field to be more specific. A good title would be
    «Enable the computation of spectra» (<40 characters is perfect!),
    while the comments can be (and should be) longer.
    
-   Once you have created the pull request, you can sit and enjoy your
    time, while your colleagues are reviewing your work. If they ask
    for changes, you can create new commits with `git commit`, and
    they will all go into the branch `compute_spectra`. Just run `git
    push` (without the `--set-upstream ...` part, `git` already knows
    about it) to publish the new commits in the existing pull request.
    
-   When the pull request is merged, you can abandon your branch: it's
    useless now. Run the following command:
    
    ```
    git checkout master
    ```
    
    and you will be back to the `master` branch.
