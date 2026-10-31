#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GLFM Project
# Copyright (c) 2026 Tuomas Lähteenmäki
# Version 1.1.0
#
# https://codeberg.org/lahtis/GLFM
# Licensed under the MIT License.
#
# Alias module: re-exports set_uralic_langs from is_uralic.
# Kept for backward compatibility with code that imports
# `from glfm.logic.set_uralic_langs import set_uralic_langs`.
#

from .is_uralic import set_uralic_langs

__all__ = ["set_uralic_langs"]
