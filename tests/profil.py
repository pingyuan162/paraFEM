import numpy as np
import meshpy.triangle as triangle

from openglider.airfoil import Profile2D
from openglider.utils.distribution import Distribution

import paraEigen as eigen
import paraBEM.pan2d as bem
import paraBEM
import paraFEM as fem

import matplotlib.tri as mtri
import matplotlib.pyplot as plt

# parameters

numpoints = 80
insert_values = [0.11, 0.27, 0.5, 0.75]

# 1: erstelle ein profil

dist = Distribution.from_nose_cos_distribution(numpoints, 0.2)
dist.insert_values(insert_values)
fixed = [list(dist.data).index(value) for value in insert_values]
boundary = range(len(dist))

airfoil = Profile2D.compute_trefftz(-0.1, 0.2, 100)
airfoil.x_values = dist

# 2: berechne druckverteilung (bem)
vertices = [paraBEM.PanelVector2(*point) for point in airfoil.data[:-1]]
vertices.append(vertices[0])
vertices[0].wake_vertex = True

panels = [paraBEM.Panel2(vertices[i:i + 2]) for i in range(len(vertices) - 1)]
case = bem.DirichletDoublet0Source0Case2(panels)
case.v_inf = eigen.vector2(1, 0.2)
case.run()
pressure = [0.01 * panel.cp * panel.l * 1.2 * 11**2 / 2 for panel in case.panels]

# 3: mesh das profil

points = airfoil.data[:-1]
edges = np.array(range(len(points)))
edges = np.array([edges, edges + 1]).T
edges[-1, -1] = 0

info = triangle.MeshInfo()
info.set_points(points, range(len(points)))
info.set_facets(edges)

mesh = triangle.build(info, allow_boundary_steiner=False, min_angle=20, max_volume=0.001)

mesh_points = list(mesh.points)
triangles = list(mesh.elements)


# 4: fem mesh

mat1 = fem.TrussMaterial(1000)
mat1.rho = 0.01
mat1.d_structural = 0.000
mat1.d_velocity = 20

mat2 = fem.MembraneMaterial(1000, 0.4)
mat2.rho = 0.01
mat2.d_structural = 0.000
mat2.d_velocity = 10

nodes = [fem.Node(point[0], point[1], 0) for point in mesh_points]
elements = [fem.Membrane3([nodes[index] for index in tri], mat2) for tri in triangles]
nodes.append(fem.Node(0.27, -2, 0))

print("number of elements: ", len(elements))

# 5: boundary conditions
lines = []
for i, node in enumerate(nodes):
    if i in fixed:
        n = fem.Node(*(node.position + eigen.vector3(0, -0.1, 0)))
        n.fixed = eigen.vector3(0, 0, 0)
        line = fem.Truss([nodes[i], n], mat1)
        lines.append(line)
    node.fixed = eigen.vector3(1, 1, 0)
for i in boundary[:-1]:
    force = pressure[i] / 2 * panels[i].n
    nodes[i].add_external_force(eigen.vector3(force.x, force.y, 0))
    nodes[i + 1].add_external_force(eigen.vector3(force.x, force.y, 0))

# 6: case
case = fem.Case(elements + lines)

writer = fem.vtkWriter("/tmp/paraFEM/profil_test")
writer.writeCase(case, 0.0)

steps = 1000
steps_ramp = 100

line_forces = []

for i in range(steps):
    ramp = 1 - (i < steps_ramp) * (1 - float(i) / steps_ramp)
    case.explicitStep(1.40675e-05, ramp)
    if (i % 2) == 0:
        print(i)
        line_forces.append([l.getStress().norm() for l in lines])
        writer.writeCase(case, 0.)

plt.plot(line_forces)
plt.show()

x, y = np.array(mesh_points).T
triang = mtri.Triangulation(x, y, triangles)

plt.plot(*airfoil.data.T, marker="x")
plt.triplot(triang, lw=0.5, color='0')
plt.axes().set_aspect('equal', 'datalim')
plt.show()

