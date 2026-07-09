# SPDX-FileCopyrightText: 2026 Ralf Habacker <ralf.habacker@freenet.de>
#
# SPDX-License-Identifier: BSD-2-Clause

TARGETS = check-imports format lint reuse sort-imports
.PHONY: ${TARGETS}
${TARGETS}:
	@tox -e $@

