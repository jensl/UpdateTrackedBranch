UpdateTrackedBranch
===================

UpdateTrackedBranch is an extension for the [Critic code review system][critic].
Its purpose is to improve the responsiveness of Critic's tracking of branches in
remote Git repositories by having those remote repositories tell Critic about
updated refs, so that Critic can schedule immediate updates.

Installation
------------

To add the extension to a Critic system, a user should create a directory named
`CriticExtensions` in his/her `$HOME` on the Critic server, and clone the
UpdateTrackedBranch repository into that directory.  If done correctly, the file
`$HOME/CriticExtensions/UpdateTrackedBranch/MANIFEST` should exist.  Also,
`$HOME` should be world executable, and `$HOME/CriticExtensions` and everything
under it should be world readable (and directories executable) so that the
Critic system is able to find and use the extension.

A Critic system administrator can also add the extension as a system extension
by doing something similar such that
`/var/lib/critic/extensions/UpdateTrackedBranch/MANIFEST` exists.

For more information about Critic extensions, see the [extensions tutorial]
[tutorial].  This tutorial is also available in any Critic system that is
sufficiently up-to-date to have extension support.

Usage
-----

The extension contains a script, `hooks/post-receive-or-update`, that should be
installed as a Git hook in the remote repository (not in Critic's repository.)
For more details, and information on how to configure it properly, see the
documentation in the script.

It's typically best if the Git hook script can access the Critic system
anonymously to notify about updated refs.  For that to work, the Critic system
needs to allow anonymous access.  Also, a Critic system administrator needs to
install the extension "universally" for it to be available anonymously.


[critic]: https://github.com/jensl/critic "Critic on GitHub"
[tutorial]: https://critic-review.org/tutorial?item=extensions "Extensions tutorial"
