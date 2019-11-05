deployment
----------

Continuous integration for this codebase is handled by appveyor (configured in appveyor.yml). Whenever a commit is pushed to master or a pull request thereto, appveyor builds the project by running fbs freeze. Whenever a tag of the format vX.Y.Z is pushed, the tag is promoted to a github release and the built windows executable is posted as a zip archive. This executable can then be downloaded and run.

Appveyor builds for this project are not rolling! Avoid making lots of small commits to e.g. a pr branch in rapid sequence.