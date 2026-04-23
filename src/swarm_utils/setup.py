from setuptools import setup

package_name = 'swarm_utils'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='swarm',
    maintainer_email='swarm@example.com',
    description='ROS 2 swarm_utils module',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'experiment_logger = swarm_utils.experiment_logger:main',
            'communication_emulator = swarm_utils.communication_emulator:main',
            'swarm_state_publisher = swarm_utils.swarm_state_publisher:main',
        ],
    },
)