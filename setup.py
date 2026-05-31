from setuptools import find_packages, setup

setup(
    name="promptforge",
    version="0.1.0",
    description="Open-source prompt engineering studio with guardrails",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
)
