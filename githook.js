/*

Copyright 2014 Jens Lindström, Opera Software ASA

The UpdateTrackedBranch extensions to the Critic code review system is licensed
under the Apache License, version 2.0.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

*/

"use strict";

var remote_transforms = [

  // ssh://HOST/PATH => HOST:/PATH
  { regexp: new RegExp("^ssh://([^/]+)(?=/)"),
    replacement: "$1:" },

  // USER@HOST:/PATH => HOST:/PATH
  { regexp: new RegExp("^[^@]+@"),
    replacement: "" },

  // HOST:/home/USER/PATH => HOST:~USER/PATH
  { regexp: new RegExp("^([^:]+:)/home/"),
    replacement: "$1~" },

  // Add a trailing ".git" if it's missing.
  { regexp: new RegExp("(?!\\.git)....$"),
    replacement: "$1.git" }

];

var name_transforms = [

  // refs/heads/NAME => NAME
  { regexp: new RegExp("^refs/heads/(.*)$"),
    replacement: "$1" }

];

function main(method, path, query) {
  if (method != "POST")
    return;

  var data = JSON.parse(read());

  writeln("200");
  writeln("Content-Type: text/json");
  writeln();

  var result;

  try {
    var remote = data.remote;
    remote_transforms.forEach(function (transform) {
      remote = remote.replace(transform.regexp, transform.replacement);
    });

    var name = data.name;
    name_transforms.forEach(function (transform) {
      name = name.replace(transform.regexp, transform.replacement);
    });

    var tracked_branch = critic.TrackedBranch.find({
      remote: remote,
      name: name
    });

    result = {
      status: "ok",
      debug: JSON.stringify([remote, name])
    };

    if (tracked_branch) {
      result.branch = tracked_branch.branch.name;

      if (tracked_branch.review)
	result.review = format('r/%(id)d "%(summary)s"', tracked_branch.review);

      if (tracked_branch.updating)
	result.update_ongoing = true;

      if (tracked_branch.disabled) {
	result.disabled = true;
      } else if (tracked_branch.pending) {
	result.update_pending = true;
      } else if (data.trigger) {
	tracked_branch.triggerUpdate();
	result.update_triggered = true;
      }

      var log_entry = tracked_branch.getLogEntry(data.value);
      if (log_entry) {
	result.hook_output = log_entry.hookOutput;
	result.update_successful = log_entry.successful;
      }
    }
  } catch (error) {
    result = {
      status: "error",
      error: error.message
    };
  }

  write("%r", result);
}
