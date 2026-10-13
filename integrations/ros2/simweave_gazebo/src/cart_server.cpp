// MIT. A dedicated Gazebo server per experiment, controlled through ROS services.
#include <chrono>
#include <csignal>
#include <cmath>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
#ifdef __linux__
#include <sys/prctl.h>
#include <unistd.h>
#endif

#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Joint.hh>
#include <gz/sim/Server.hh>
#include <gz/sim/ServerConfig.hh>
#include <gz/sim/System.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/config.hh>
#include <rclcpp/rclcpp.hpp>
#include <simulation_interfaces/srv/get_simulator_features.hpp>
#include <simulation_interfaces/srv/reset_simulation.hpp>
#include <simulation_interfaces/srv/set_simulation_state.hpp>
#include <simulation_interfaces/srv/step_simulation.hpp>
#include "simweave_gazebo/srv/configure_cart.hpp"
#include "simweave_gazebo/srv/get_cart_state.hpp"
#include "simweave_gazebo/srv/set_cart_force.hpp"

namespace si = simulation_interfaces::srv;
namespace sw = simweave_gazebo::srv;

class CartSystem : public gz::sim::System,
                   public gz::sim::ISystemPreUpdate,
                   public gz::sim::ISystemPostUpdate {
 public:
  double position = 0, velocity = 0, force = 0, time = 0;
  bool observed = false;
  gz::sim::Entity entity = gz::sim::kNullEntity;
  void PreUpdate(const gz::sim::UpdateInfo &, gz::sim::EntityComponentManager &ecm) override {
    if (entity == gz::sim::kNullEntity) {
      entity = ecm.EntityByComponents(gz::sim::components::Joint(),
                                     gz::sim::components::Name("slide"));
      if (entity == gz::sim::kNullEntity) throw std::runtime_error("cart joint missing");
      gz::sim::Joint joint(entity);
      joint.EnablePositionCheck(ecm);
      joint.EnableVelocityCheck(ecm);
      joint.ResetPosition(ecm, {position});
      joint.ResetVelocity(ecm, {velocity});
    }
    gz::sim::Joint(entity).SetForce(ecm, {force});
  }
  void PostUpdate(const gz::sim::UpdateInfo &info,
                  const gz::sim::EntityComponentManager &ecm) override {
    if (info.paused) return;
    auto p = gz::sim::Joint(entity).Position(ecm);
    auto v = gz::sim::Joint(entity).Velocity(ecm);
    observed = p && v && p->size() == 1 && v->size() == 1;
    if (observed) {
      position = p->at(0);
      velocity = v->at(0);
      time = std::chrono::duration<double>(info.simTime).count();
      observed = std::isfinite(position) && std::isfinite(velocity);
    }
  }
};

class CartServer : public rclcpp::Node {
 public:
  CartServer() : Node("cart_server") {
    services.push_back(create_service<si::GetSimulatorFeatures>(
        "get_simulator_features",
        [](si::GetSimulatorFeatures::Request::SharedPtr,
           si::GetSimulatorFeatures::Response::SharedPtr res) {
          res->features.features = {20, 25, 26, 31, 32};
          res->features.custom_info = "simweave-cart/1; full reset; paused finite stepping";
        }));
    serve<sw::ConfigureCart>("configure_cart", [this](const auto &req, auto &res) {
      bounded(req.timestep, 0.001, 0.1);
      if (std::abs(req.timestep * 1e9 - std::round(req.timestep * 1e9)) > 1e-6)
        throw std::runtime_error("timestep precision");
      bounded(req.mass, 0.1, 1000);
      bounded(req.damping, 0, 10);
      bounded(req.initial_position, -100, 100);
      bounded(req.initial_velocity, -100, 100);
      parameters = req;
      reset();
      res.adapter_version = std::string("gazebo-") + GZ_SIM_VERSION_FULL + ";cart-1";
    });
    serve<si::ResetSimulation>("reset_simulation", [this](const auto &req, auto &) {
      // This fixture implements only an all-scopes reset. Partial resets are rejected.
      if (req.scope != 0 && req.scope != 255) throw std::runtime_error("reset scope");
      reset();
    });
    serve<si::SetSimulationState>("set_simulation_state", [](const auto &req, auto &) {
      if (req.state.state != 2) throw std::runtime_error("finite stepping only");
    });
    serve<sw::SetCartForce>("set_cart_force", [this](const auto &req, auto &) {
      require_server();
      bounded(req.force, -650000, 650000);
      if (req.expected_step != step || armed) throw std::runtime_error("force sequence");
      cart->force = req.force;
      armed = true;
    });
    serve<si::StepSimulation>("step_simulation", [this](const auto &req, auto &) {
      require_server();
      if (req.steps < 1 || req.steps > 20000 - step) throw std::runtime_error("step bound");
      for (uint64_t i = 0; i < req.steps; ++i) {
        cart->observed = false;
        if (!server->RunOnce(false) || !cart->observed) throw std::runtime_error("physics step");
        ++step;
      }
      armed = false;
      cart->force = 0;
      server->SetPaused(true);
    });
    serve<sw::GetCartState>("get_cart_state", [this](const auto &, auto &res) {
      require_server();
      res.step = step;
      res.time = cart->time;
      res.position = cart->position;
      res.velocity = cart->velocity;
    });
  }
 private:
  std::vector<rclcpp::ServiceBase::SharedPtr> services;
  std::unique_ptr<gz::sim::Server> server;
  std::shared_ptr<CartSystem> cart;
  sw::ConfigureCart::Request parameters;
  uint64_t step = 0;
  bool armed = false;

  static void bounded(double value, double lo, double hi) {
    if (!std::isfinite(value) || value < lo || value > hi) throw std::runtime_error("invalid value");
  }
  void require_server() {
    if (!server) throw std::runtime_error("cart not configured");
  }
  template<class Service, class Function> void serve(const std::string &name, Function fn) {
    services.push_back(create_service<Service>(name,
      [fn](typename Service::Request::SharedPtr req, typename Service::Response::SharedPtr res) {
        try {
          fn(*req, *res);
          res->result.result = 1;
        } catch (const std::exception &) {
          res->result.result = 2;
          res->result.error_message = "cart operation rejected or failed";
        }
      }));
  }
  void reset() {
    bounded(parameters.mass, 0.1, 1000);  // No reset before ConfigureCart.
    server.reset();
    cart = std::make_shared<CartSystem>();
    cart->position = parameters.initial_position;
    cart->velocity = parameters.initial_velocity;
    step = 0;
    armed = false;
    std::ostringstream sdf;
    sdf << std::setprecision(17)
        << "<sdf version='1.9'><world name='simweave'><gravity>0 0 0</gravity>"
        << "<physics name='physics' type='ignored'><max_step_size>" << parameters.timestep
        << "</max_step_size><real_time_factor>0</real_time_factor></physics>"
        << "<plugin filename='gz-sim-physics-system' name='gz::sim::systems::Physics'/>"
        << "<model name='cart'><link name='body'><inertial><mass>" << parameters.mass
        << "</mass><inertia><ixx>1</ixx><iyy>1</iyy><izz>1</izz></inertia></inertial></link>"
        << "<joint name='slide' type='prismatic'><parent>world</parent><child>body</child>"
        << "<axis><xyz>1 0 0</xyz><dynamics><damping>" << parameters.damping
        << "</damping></dynamics><limit><lower>-1e12</lower><upper>1e12</upper>"
        << "</limit></axis></joint></model></world></sdf>";
    gz::sim::ServerConfig config;
    config.SetPhysicsEngine("gz-physics-dartsim-plugin");
    config.SetSeed(0);  // This fixture has no native randomization; sensor noise lives in Python.
    config.SetSdfString(sdf.str());
    server = std::make_unique<gz::sim::Server>(config);
    if (!server->AddSystem(cart).value_or(false) || !server->RunOnce(true))
      throw std::runtime_error("cart initialization failed");
    server->SetUpdatePeriod(std::chrono::steady_clock::duration::zero());
  }
};

int main(int argc, char **argv) {
#ifdef __linux__
  // A killed worker must not leave a native simulation process behind.
  const auto parent = getppid();
  // PID 1 is a valid experiment owner inside a container.
  if (prctl(PR_SET_PDEATHSIG, SIGTERM) != 0 || getppid() != parent) return 1;
#endif
  rclcpp::init(argc, argv);
  // Single-threaded callbacks serialize force acknowledgement, stepping, and observations.
  rclcpp::spin(std::make_shared<CartServer>());
  rclcpp::shutdown();
}
