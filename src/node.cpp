#include "node.h"
#include <iostream>


namespace paraFEM {

Node::Node(double x, double y, double z)
{
    position = Eigen::Vector3d(x, y, z);
    velocity.setZero();
    acceleration.setZero();
    massInfluence = 0.;
    fixed.setOnes();
    externalForce.setZero();
    internalForce.setZero();
}

void Node::solveEquilibrium(double h, double externalFactor)
{
    acceleration = 1. / massInfluence * (externalForce * externalFactor - internalForce);
    velocity += h * (acceleration.cwiseProduct(fixed));   // at time t + 0.5h
    position += velocity * h;       // at time t + 1
}

void Node::add_external_force(Vector3 force)
{
    externalForce += force;
}

}