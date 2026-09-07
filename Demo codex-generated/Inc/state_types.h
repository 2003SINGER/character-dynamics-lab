#pragma once

#include <string>

enum class CommitmentStatus { None, Active, Suspended };

struct TaskCommitment {
    CommitmentStatus status = CommitmentStatus::None;
    std::string task_id;
    std::string reason;
    int started_at_total_minutes = -1;
    int suspended_decision_points = 0;
};

struct CharacterState {
    double boredom = 0.55;
    double fatigue = 0.15;
    double task_pressure = 0.55;
    double satisfaction = 0.45;
    double hunger = 0.25;
    double bathroom_urge = 0.15;
    double anxiety = 0.20;
    double screen_strain = 0.05;
    double purchase_urge = 0.10;
    TaskCommitment commitment;
};
