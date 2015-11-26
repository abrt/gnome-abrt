# Contributing to gnome-abrt

Adopted from http://www.contribution-guide.org/

BSD, Copyright (c) 2015 Jeff Forcier

## Submitting bugs

### Due diligence

Before submitting a bug, please do the following:

* Perform **basic troubleshooting** steps:

    * **Make sure you're on the latest version.** If you're not on the most
      recent version, your problem may have been solved already! Upgrading is
      always the best first step.
    * **Try older versions.** If you're already *on* the latest release, try
      rolling back a few minor versions (e.g. if on 1.7, try 1.5 or 1.6) and
      see if the problem goes away. This will help the devs narrow down when
      the problem first arose in the commit log.
    * **Try switching up dependency versions.** If the software in question has
      dependencies (other libraries, etc) try upgrading/downgrading those as
      well.

* **Search the project's bug/issue tracker** to make sure it's not a known issue.
* If you don't find a pre-existing issue, consider **checking with the mailing
  list and/or IRC channel** in case the problem is non-bug-related.
* Consult [README.md](README.md) for links to bugtracker, mailinglist or IRC.

### What to put in your bug report

Make sure your report gets the attention it deserves: bug reports with missing
information may be ignored or punted back to you, delaying a fix. The below
constitutes a bare minimum; more info is almost always better:

* **What version of the core programming language interpreter/compiler are you
  using?** For example, if it's a Python project, are you using Python 2.7.3?
  Python 3.3.1? PyPy 2.0?
* **What operating system are you on?** Make sure to include release and distribution.
* **Which version or versions of the software are you using?** Ideally, you
  followed the advice above and have ruled out (or verified that the problem
  exists in) a few different versions.
* **How can the developers recreate the bug on their end?** If possible,
  include a copy of your code, the command you used to invoke it, and the full
  output of your run (if applicable.)

    * A common tactic is to pare down your code until a simple (but still
      bug-causing) "base case" remains. Not only can this help you identify
      problems which aren't real bugs, but it means the developer can get to
      fixing the bug faster.


## Contributing changes

### Code formatting

Please make sure pylint does not produce any warning.

### Documentation

Every patch must have either comprehensive commit message saying what is being
changed and why or a link (an issue number on Github) to a bug report where
this information is available.

### Full example

Here's an example workflow for a project `gnome-abrt` hosted on Github
Your username is `yourname` and you're submitting a basic bugfix or feature.

* Hit 'fork' on Github, creating e.g. `yourname/gnome-abrt`.
* `git clone git@github.com:yourname/gnome-abrt`
* `cd gnome-abrt`
* [Hack, hack, hack](HACKING.md)
* Run `make check`
* `git commit -m "Foo the bars"`
* `git push origin HEAD` to get it back up to your fork
* Visit Github, click handy "Pull request" button.
* In the description field, write down issue number (if submitting code fixing
  an existing issue) or describe the issue + your fix (if submitting a wholly
  new bugfix).
* Hit 'submit'! And please be patient - the maintainers will get to you when
  they can.
