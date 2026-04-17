from setuptools import find_packages, setup

package_name = 'swarm_perception'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='swarm',
    maintainer_email='swarm@example.com',
    description='ROS 2 swarm_perception module',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            # Раскомментируйте при наличии узлов:
            # 'perception_node = swarm_perception.perception_node:main',
        ],
    },
)
