import warnings

# Suppress build123d warnings about boolean operations being unable to clean shapes.
# These are informational - the shapes are still valid and usable.
warnings.filterwarnings("ignore", message="Boolean operation unable to clean")
warnings.filterwarnings("ignore", message="Unable to clean")
