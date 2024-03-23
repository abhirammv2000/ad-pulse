class Config:
    DEBUG = False
    # Add other configuration options here

class DevelopmentConfig(Config):
    DEBUG = True
    # Add development-specific configuration options here

class ProductionConfig(Config):
    DEBUG = False
    # Add production-specific configuration options here

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    # Add additional configurations as needed
}
