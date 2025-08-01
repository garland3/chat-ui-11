#!/usr/bin/env python3
"""
Test XLSX support and additional libraries in code execution environment.
"""
import sys
import os
import unittest
from pathlib import Path

# Add code-executor to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp', 'code-executor'))

# Ensure logs directory exists
logs_dir = Path(__file__).parent.parent / 'logs'
logs_dir.mkdir(exist_ok=True)
(logs_dir / 'app.log').touch(exist_ok=True)

from main import check_code_security


class TestXlsxSupport(unittest.TestCase):
    """Test cases for XLSX support and additional libraries."""

    def test_xlsx_libraries_allowed(self):
        """Test that openpyxl and xlsx-related libraries are allowed."""
        test_cases = [
            "import openpyxl",
            "from openpyxl import Workbook",
            "import pandas as pd; df = pd.read_excel('file.xlsx')",
            "import pandas as pd; df.to_excel('file.xlsx', engine='openpyxl')",
        ]
        
        for code in test_cases:
            with self.subTest(code=code):
                violations = check_code_security(code)
                self.assertEqual([], violations, f"Code should be allowed: {code}")

    def test_scipy_allowed(self):
        """Test that scipy is allowed."""
        test_cases = [
            "import scipy",
            "import scipy.stats",
            "from scipy import stats",
            "from scipy.stats import pearsonr",
        ]
        
        for code in test_cases:
            with self.subTest(code=code):
                violations = check_code_security(code)
                self.assertEqual([], violations, f"Scipy code should be allowed: {code}")

    def test_sklearn_allowed(self):
        """Test that sklearn is allowed."""
        test_cases = [
            "import sklearn",
            "from sklearn import linear_model",
            "from sklearn.linear_model import LinearRegression",
            "import sklearn.ensemble",
        ]
        
        for code in test_cases:
            with self.subTest(code=code):
                violations = check_code_security(code)
                self.assertEqual([], violations, f"Sklearn code should be allowed: {code}")

    def test_pil_allowed(self):
        """Test that PIL/Pillow is allowed."""
        test_cases = [
            "import PIL",
            "from PIL import Image",
            "from PIL import ImageDraw",
            "import pillow",
        ]
        
        for code in test_cases:
            with self.subTest(code=code):
                violations = check_code_security(code)
                self.assertEqual([], violations, f"PIL code should be allowed: {code}")

    def test_combined_data_analysis_workflow(self):
        """Test a complete data analysis workflow with all new libraries."""
        code = """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
from sklearn.linear_model import LinearRegression
from PIL import Image, ImageDraw
import openpyxl

# Read Excel file
df = pd.read_excel('data.xlsx')

# Statistical analysis
correlation, p_value = stats.pearsonr(df.iloc[:, 0], df.iloc[:, 1])

# Machine learning
X = df.iloc[:, :-1].values
y = df.iloc[:, -1].values
model = LinearRegression().fit(X, y)

# Create visualization
plt.figure()
plt.scatter(X[:, 0], y)
plt.savefig('scatter.png')
plt.close()

# Create image with PIL
img = Image.new('RGB', (100, 100), 'white')
draw = ImageDraw.Draw(img)
draw.text((10, 10), 'Analysis Complete', fill='black')
img.save('report.png')

# Save results to Excel
results = pd.DataFrame({'predictions': model.predict(X)})
results.to_excel('results.xlsx', engine='openpyxl')
"""
        
        violations = check_code_security(code)
        self.assertEqual([], violations, "Complete workflow should be allowed")

    def test_forbidden_modules_still_blocked(self):
        """Test that dangerous modules are still blocked."""
        forbidden_cases = [
            "import os",
            "import sys",
            "import subprocess",
            "import socket",
            "import requests",
            "import pickle",
            "import threading",
        ]
        
        for code in forbidden_cases:
            with self.subTest(code=code):
                violations = check_code_security(code)
                self.assertNotEqual([], violations, f"Dangerous code should be blocked: {code}")

    def test_forbidden_functions_still_blocked(self):
        """Test that dangerous functions are still blocked."""
        forbidden_cases = [
            "eval('1+1')",
            "exec('print(1)')",
            "__import__('os')",
            "getattr(object, '__class__')",
        ]
        
        for code in forbidden_cases:
            with self.subTest(code=code):
                violations = check_code_security(code)
                self.assertNotEqual([], violations, f"Dangerous function should be blocked: {code}")


if __name__ == '__main__':
    unittest.main()