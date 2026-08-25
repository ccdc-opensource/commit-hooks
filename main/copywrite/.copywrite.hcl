schema_version = 1

project {
  copyright_holder = "The Cambridge Crystallographic Data Centre (CCDC)"

  header_ignore = [
    ".git/**",
    ".github/**",
    "**/bin/**",
    "**/obj/**",
    "**/packages/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/.venv/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/*.Designer.cs",
    "**/*.g.cs",
    "**/*.generated.*",
    "**/*.min.js",
    "**/*.lock",
  ]
}

rule {
  paths = ["**/*.py", "**/*.sh", "**/*.bash", "**/*.yaml", "**/*.yml"]
  license_header = "main/copywrite/headers/ccdc_hash.tmpl"
}

rule {
  paths = ["**/*.js", "**/*.ts", "**/*.cs", "**/*.cpp", "**/*.cxx", "**/*.cc", "**/*.h", "**/*.hpp"]
  license_header = "main/copywrite/headers/ccdc_slash.tmpl"
}