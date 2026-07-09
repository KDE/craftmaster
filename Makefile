# SPDX-FileCopyrightText: 2026 Ralf Habacker <ralf.habacker@freenet.de>
#
# SPDX-License-Identifier: BSD-2-Clause

TARGETS = check-imports format lint reuse sort-imports
.PHONY: ${TARGETS}
${TARGETS}:
	@tox -e $@

.PHONY: test
test:
	python3 -m unittest tests/test_craftmaster.py
	python3 -m py_compile CraftMaster.py Config.py tests/test_craftmaster.py
	git diff --check

