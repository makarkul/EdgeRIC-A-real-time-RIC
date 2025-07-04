import argparse
import hydra
import gym
import os
import sys
import pickle
import time
import debugpy
import logging
import torch
import numpy as np
import zmq

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import math
import time
from edgeric_messenger import *

torch.set_printoptions(precision=2)
np.set_printoptions(suppress=True)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import *
from models.mlp_policy import Policy
from models.mlp_critic import Value
from models.mlp_policy_disc import DiscretePolicy
from core.ppo import ppo_step
from core.common import estimate_advantages
from core.agent_original import Agent

from stream_rl.registry import ENVS
from stream_rl.plots import (
    visualize_edgeric_training,
    visualize_edgeric_evaluation,
    plot_cdf,
    visualize_policy_cqi,
    visualize_policy_backlog_len,
)

# A logger for this file
log = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description="PyTorch PPO Latency Optimization for EdgeRIC")
parser.add_argument(
    "--env-name",
    default="EdgeRIC_Latency",
    metavar="G",
    help="name of the environment to run",
)
parser.add_argument("--model-path", metavar="G", help="path of pre-trained model")
parser.add_argument(
    "--render", action="store_true", default=False, help="render the environment"
)
parser.add_argument(
    "--log-std",
    type=float,
    default=-0.0,
    metavar="G",
    help="log std for the policy (default: -0.0)",
)
parser.add_argument(
    "--gamma",
    type=float,
    default=0.95,  # Higher discount for latency optimization
    metavar="G",
    help="discount factor (default: 0.95)",
)
parser.add_argument(
    "--tau", type=float, default=0.95, metavar="G", help="gae (default: 0.95)"
)
parser.add_argument(
    "--l2-reg",
    type=float,
    default=1e-3,  # Lower regularization for latency sensitivity
    metavar="G",
    help="l2 regularization regression (default: 1e-3)",
)
parser.add_argument(
    "--learning-rate",
    type=float,
    default=2e-3,  # Slightly lower learning rate for stability
    metavar="G",
    help="learning rate (default: 2e-3)",
)
parser.add_argument(
    "--clip-epsilon",
    type=float,
    default=0.15,  # Tighter clipping for latency optimization
    metavar="N",
    help="clipping epsilon for PPO",
)
parser.add_argument(
    "--num-threads",
    type=int,
    default=1,
    metavar="N",
    help="number of threads for agent (default: 1)",
)
parser.add_argument(
    "--seed", type=int, default=42, metavar="N", help="random seed (default: 42)"
)
parser.add_argument(
    "--min-batch-size",
    type=int,
    default=2048,
    metavar="N",
    help="minimal batch size per PPO update (default: 2048)",
)
parser.add_argument(
    "--eval-batch-size",
    type=int,
    default=2048,
    metavar="N",
    help="minimal batch size for evaluation (default: 2048)",
)
parser.add_argument(
    "--max-iter-num",
    type=int,
    default=100,
    metavar="N",
    help="maximal number of main iterations (default: 100)",
)
parser.add_argument(
    "--log-interval",
    type=int,
    default=1,
    metavar="N",
    help="interval between training status logs (default: 1)",
)
parser.add_argument(
    "--save-model-interval",
    type=int,
    default=10,  # Save more frequently for latency models
    metavar="N",
    help="interval between saving model (default: 10)",
)
parser.add_argument("--gpu-index", type=int, default=0, metavar="N")
args = parser.parse_args()

@hydra.main(config_path="conf", config_name="edge_ric_latency", version_base=None)
def main(conf):

    dtype = torch.float32
    torch.set_default_dtype(dtype)
    device = (
        torch.device("cuda", index=args.gpu_index)
        if torch.cuda.is_available()
        else torch.device("cpu")
    )
    if torch.cuda.is_available():
        torch.cuda.set_device(args.gpu_index)

    def update_params(batch, i_iter):
        states = torch.from_numpy(np.stack(batch.state)).to(dtype).to(device)
        actions = torch.from_numpy(np.stack(batch.action)).to(dtype).to(device)
        rewards = torch.from_numpy(np.stack(batch.reward)).to(dtype).to(device)
        masks = torch.from_numpy(np.stack(batch.mask)).to(dtype).to(device)
        with torch.no_grad():
            values = value_net(states)
            fixed_log_probs = policy_net.get_log_prob(states, actions)

        """get advantage estimation from the trajectories"""
        advantages, returns = estimate_advantages(
            rewards, masks, values, args.gamma, args.tau, device
        )

        """perform mini-batch PPO update"""
        optim_iter_num = int(math.ceil(states.shape[0] / optim_batch_size))
        for _ in range(optim_epochs):
            perm = np.arange(states.shape[0])
            np.random.shuffle(perm)
            perm = LongTensor(perm).to(device)

            states, actions, returns, advantages, fixed_log_probs = (
                states[perm].clone(),
                actions[perm].clone(),
                returns[perm].clone(),
                advantages[perm].clone(),
                fixed_log_probs[perm].clone(),
            )

            for i in range(optim_iter_num):
                ind = slice(
                    i * optim_batch_size,
                    min((i + 1) * optim_batch_size, states.shape[0]),
                )
                states_b, actions_b, advantages_b, returns_b, fixed_log_probs_b = (
                    states[ind],
                    actions[ind],
                    advantages[ind],
                    returns[ind],
                    fixed_log_probs[ind],
                )

                ppo_step(
                    policy_net,
                    value_net,
                    optimizer_policy,
                    optimizer_value,
                    1,
                    states_b,
                    actions_b,
                    returns_b,
                    advantages_b,
                    fixed_log_probs_b,
                    args.clip_epsilon,
                    args.l2_reg,
                )

    def main_loop():
        hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
        output_dir = hydra_cfg["run"]["dir"]
         # Ensure the directory exists
        if not os.path.exists(output_dir):
            print(f"Creating directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        else:
            print(f"Directory already exists: {output_dir}")
            
        ppo_rewards = []
        latency_metrics = []  # Track latency performance
        
        for i_iter in range(conf["num_iters"]):
            """generate multiple trajectories that reach the minimum batch_size"""
            batch, log_train = agent.collect_samples(
                args.min_batch_size, render=args.render
            )
            t0 = time.time()
            update_params(batch, i_iter)
            t1 = time.time()
            """evaluate with deterministic action (remove noise for exploration)"""
            _, log_eval = agent.collect_samples(args.eval_batch_size, mean_action=False)
            t2 = time.time()
            
            # Normalize reward for comparison
            ppo_rewards.append(log_eval["avg_reward"]/5000) 
            
            # Extract latency information if available
            avg_latency = log_eval.get("avg_latency", 0)
            latency_metrics.append(avg_latency)
            
            if i_iter % args.log_interval == 0:
                log.info(
                    "{}\tT_sample {:.4f}\tT_update {:.4f}\tT_eval {:.4f}\ttrain_R_min {:.2f}\ttrain_R_max {:.2f}\ttrain_R_avg {:.2f}\teval_R_avg {:.2f}\teval_latency {:.2f}μs".format(
                        i_iter,
                        log_train["sample_time"],
                        t1 - t0,
                        t2 - t1,
                        log_train["min_reward"],
                        log_train["max_reward"],
                        log_train["avg_reward"],
                        log_eval["avg_reward"],
                        avg_latency,
                    )
                )

            # Save best model based on reward (which includes latency optimization)
            if max(ppo_rewards) == log_eval["avg_reward"]/5000:
                torch.save(policy_net, os.path.join(output_dir, "model_best.pt"))
                # Also save latency-specific info
                with open(os.path.join(output_dir, "best_model_info.txt"), "w") as f:
                    f.write(f"Best model at iteration {i_iter}\n")
                    f.write(f"Reward: {log_eval['avg_reward']}\n")
                    f.write(f"Average Latency: {avg_latency}μs\n")

            # Save model checkpoints
            if (
                args.save_model_interval > 0
                and (i_iter + 1) % args.save_model_interval == 0
            ):
                checkpoint_path = os.path.join(output_dir, f"model_checkpoint_{i_iter}.pt")
                torch.save(policy_net, checkpoint_path)
                
                # Save training metrics
                metrics_data = {
                    'rewards': ppo_rewards,
                    'latencies': latency_metrics,
                    'iteration': i_iter
                }
                with open(os.path.join(output_dir, f"metrics_{i_iter}.pkl"), "wb") as f:
                    pickle.dump(metrics_data, f)

            # Save specific iterations for analysis
            if i_iter == 1 or i_iter == 15 or i_iter == 50:
                filename = f"model_latency_{i_iter}.pt"
                model_path = os.path.join(output_dir, filename)
                torch.save(policy_net, model_path)

            """clean up gpu memory"""
            torch.cuda.empty_cache()
            
        return ppo_rewards, latency_metrics

    def eval_loop(num_episodes, agent_type, env_cls, env_config):
        log.info(f"\n\n Evaluating {agent_type} Agent for Latency Optimization")
        
        # Use current output directory
        hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
        output_dir = hydra_cfg["run"]["dir"]
        
        # instantiate env class
        env_config.update({"seed": 9})
        env_config.update({"cqi_trace": env_config["cqi_trace_eval"]})
        env = env_cls(env_config)
        
        if agent_type == "PPO":
            model_path = os.path.join(output_dir, "model_best.pt")
            if os.path.exists(model_path):
                model = torch.load(model_path, map_location=torch.device('cpu'))
                model.eval()
            else:
                log.error(f"Model not found at {model_path}")
                return [], []
        elif agent_type == "CQI":
            model = MaxCQIAgent(env_config["augment_state_space"])
        elif agent_type == "Pressure":
            model = MaxPressureAgent(env_config["augment_state_space"])
        elif agent_type == "LatencyAware":
            # Simple latency-aware baseline
            model = LatencyAwareAgent(env_config["augment_state_space"])

        episode_rewards = []
        episode_latencies = []
        forward_pass_times = []
        
        for episode in range(num_episodes):
            log.info(f"Episode {episode}")
            episode_reward = 0
            episode_latency_sum = 0
            episode_steps = 0
            done = False
            
            ue_data = get_metrics_multi()
            numues = len(ue_data)
            env.num_UEs = numues
            obs = env.reset()
            
            while not done:
                curr_state = obs
                if agent_type == "PPO":
                    obs_tensor = torch.from_numpy(obs)
                    obs_tensor = torch.unsqueeze(obs_tensor, dim=0)
                    
                with torch.no_grad():
                    start = time.time()
                    action = model.select_action(obs_tensor if agent_type == "PPO" else obs)
                    if agent_type == "PPO":
                        forward_pass_times.append(time.time() - start)
                        action = torch.squeeze(action)
                
                ue_data = get_metrics_multi()
                numues = len(ue_data)
                weight = np.zeros(numues * 2)
                
                # Extract metrics from ue_data
                CQIs = [data['CQI'] for data in ue_data.values()]
                RNTIs = list(ue_data.keys())
                BLs = [data['Backlog'] for data in ue_data.values()]
                # Get latencies for evaluation
                latencies = [data.get('Latency', 10000) for data in ue_data.values()]
                mbs = np.ones(numues) * 300000 
                txb = [data['Tx_brate'] for data in ue_data.values()]   
                tx_bytes = np.sum(txb)   
                        
                obs, reward, done, info = env.step(action, RNTIs, CQIs, BLs, tx_bytes, mbs)

                # Apply scheduling weights
                for ue in range(numues):
                    percentage_RBG = action[ue] / sum(action) if sum(action) > 0 else 1.0 / numues
                    weight[ue*2+1] = percentage_RBG
                    weight[ue*2] = RNTIs[ue]

                send_scheduling_weight(weight, True) 
                
                episode_reward += reward
                if 'avg_latency' in info:
                    episode_latency_sum += info['avg_latency']
                    episode_steps += 1
                
                log.info(
                    f"state: {curr_state[:6]}... action: {action} reward: {reward:.2f} latency: {info.get('avg_latency', 0):.2f}μs"
                )

            episode_reward = episode_reward / 1000.0   
            episode_rewards.append(episode_reward)
            
            avg_episode_latency = episode_latency_sum / episode_steps if episode_steps > 0 else 0
            episode_latencies.append(avg_episode_latency)
            
        log.info(f"{agent_type} Agent - Avg Reward: {np.mean(episode_rewards):.2f}, Avg Latency: {np.mean(episode_latencies):.2f}μs")
        
        if agent_type == "PPO":
            return episode_rewards, episode_latencies, forward_pass_times
        return episode_rewards, episode_latencies

    # Training loop
    num_eval_episodes = conf["num_eval_episodes"]
    num_seeds = conf["num_seeds"]
    ppo_train_rewards = []
    ppo_train_latencies = []
    env_cls = ENVS[conf["env"]]
    
    for seed in range(num_seeds):
        log.info(f"********* Training for seed {seed+1} (Latency Optimization) *********")
        """environment"""
        env_cls = ENVS[conf["env"]]
        env = env_cls(conf["env_config"])
        state_dim = env.observation_space.shape[0]
        is_disc_action = len(env.action_space.shape) == 0
        running_state = None

        """define actor and critic"""
        if args.model_path is None:
            if is_disc_action:
                policy_net = DiscretePolicy(state_dim, env.action_space.n)
            else:
                policy_net = Policy(
                    state_dim,
                    env.action_space.shape[0],
                    log_std=args.log_std,
                    activation="sigmoid",
                )
            value_net = Value(state_dim)
        else:
            policy_net, value_net, running_state = pickle.load(
                open(args.model_path, "rb")
            )
        policy_net.to(device)
        value_net.to(device)

        optimizer_policy = torch.optim.Adam(
            policy_net.parameters(), lr=args.learning_rate
        )
        optimizer_value = torch.optim.Adam(
            value_net.parameters(), lr=args.learning_rate
        )

        # optimization epoch number and batch size for PPO
        optim_epochs = 10
        optim_batch_size = 64

        """create agent"""
        agent = Agent(
            env,
            policy_net,
            device,
            running_state=running_state,
            num_threads=args.num_threads,
        )

        rewards, latencies = main_loop()
        ppo_train_rewards.append(rewards)
        ppo_train_latencies.append(latencies)
    
    if ppo_train_rewards:
        visualize_edgeric_training(ppo_train_rewards)
        
        # Save latency training data
        hydra_cfg = hydra.core.hydra_config.HydraConfig.get()
        output_dir = hydra_cfg["run"]["dir"]
        
        training_data = {
            'rewards': ppo_train_rewards,
            'latencies': ppo_train_latencies,
            'config': conf
        }
        
        with open(os.path.join(output_dir, "latency_training_results.pkl"), "wb") as f:
            pickle.dump(training_data, f)
        
        log.info(f"Training completed. Results saved to {output_dir}")
        log.info(f"Final average latency: {np.mean(latencies[-10:]) if latencies else 'N/A'}μs")

# Simple latency-aware baseline agent
class LatencyAwareAgent:
    def __init__(self, augment_state_space):
        self.augment_state_space = augment_state_space
        
    def select_action(self, obs):
        """Simple latency-aware scheduling: prioritize UEs with higher latency"""
        if self.augment_state_space:
            # obs format: [BL1, CQI1, LAT1, MB1, LP1, BL2, CQI2, LAT2, MB2, LP2, ...]
            num_ues = len(obs) // 5
            latencies = [obs[i*5 + 2] for i in range(num_ues)]  # Extract latency values
        else:
            # obs format: [BL1, CQI1, LAT1, MB1, BL2, CQI2, LAT2, MB2, ...]
            num_ues = len(obs) // 4
            latencies = [obs[i*4 + 2] for i in range(num_ues)]  # Extract latency values
        
        # Simple strategy: allocate more resources to UEs with higher latency
        if max(latencies) > 0:
            # Normalize latencies to get allocation weights
            latency_weights = np.array(latencies) / sum(latencies)
        else:
            # Equal allocation if no latency info
            latency_weights = np.ones(num_ues) / num_ues
            
        # Ensure weights sum to 1
        action = latency_weights / sum(latency_weights)
        return action

if __name__ == "__main__":
    main()
