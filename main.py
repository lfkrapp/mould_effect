import io
import imageio
import torch as pt
import matplotlib.pyplot as plt
from tqdm import tqdm


# potential
def V(X, d0, kl, kt):
    # hookean spring chain potential
    d = pt.sqrt(pt.sum(pt.square(X[1:] - X[:-1]), axis=1))
    V0 = 0.5 * kl * pt.sum(pt.square(d - d0))

    # harmonic angle potential
    R = X[1:] - X[:-1]
    r0 = pt.sqrt(pt.sum(pt.square(R[1:]), axis=1))
    r1 = pt.sqrt(pt.sum(pt.square(R[:-1]), axis=1))
    dTheta = pt.arccos(pt.sum(R[1:] * R[:-1], axis=1) / (r0 * r1 + 1e-9))
    V1 = 0.5 * kt * pt.sum(pt.square(dTheta))

    return V0 + V1

# acceleration
def A(Xi, d0, kl, kt, g):
    # reset gradients
    Xi.grad = None

    # compute potential
    Vi = V(Xi, d0, kl, kt)

    # compute gradients
    Vi.backward()
    Ai = -Xi.grad

    # add pulling force for first bead
    Ai[0,1] += -g

    return Ai


# simulation
def simulation(num_beads, num_steps, dt, d0, kl, kt, g, vy0, device=pt.device("cpu")):
    # initial positions and velocities
    Xi = pt.zeros((num_beads, 2)).to(device)
    Vi = pt.zeros((num_beads, 2)).to(device)

    # lay out beads
    Xi[:,0] = pt.linspace(0.0, -num_beads*d0, num_beads).to(device)

    # quickstart up motion
    Vi[0,1] = vy0

    # set variable with gradient requirements
    Xi.requires_grad = True

    # start simulation
    X = pt.zeros((num_steps, num_beads, 2), dtype=pt.float32)
    for i in tqdm(range(num_steps)):
        # leapfrog integration
        Ai = A(Xi, d0, kl, kt, g)
        with pt.no_grad():
            Xi += Vi * dt + 0.5 * Ai * dt * dt
        Aip1 = A(Xi, d0, kl, kt, g)
        Vip1 = Vi + 0.5 * (Ai + Aip1) * dt
        Vi = Vip1

        # save step coordinates
        X[i] = Xi.detach().cpu().clone()

    return X

# save animation
def make_animation(X, xlim, ylim, stride, gif_filepath):
    # make animation of simulation
    plt.figure(figsize=(8,5))
    with imageio.get_writer(gif_filepath, mode='I') as writer:
        for i in tqdm(range(X.shape[0])):
            # plot only every stride frames
            if (i % stride) == 0:
                # clear plot
                plt.gca().cla()
                # make plot
                plt.plot(X[i,:,0].numpy(), X[i,:,1].numpy(), '.-')
                plt.plot(xlim, [0.0,0.0], 'k--')
                plt.xlim(xlim)
                plt.ylim(ylim)
                plt.xlabel('x')
                plt.ylabel('y')
                plt.title("timestep = {}".format(i))
                # create and save image to buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150)
                # read buffer and write to gif
                buf.seek(0)
                image = imageio.imread(buf)
                writer.append_data(image)
                buf.close()
    # close figure
    plt.close()
