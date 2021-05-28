# Spice

Spice is Armada bio's [opentrons FastAPI](https://github.com/koeng101/opentronsfastapi) api. This api is deployed onto the raspberry pi in an opentrons robot and runs from the robot's IP on port 8000.

## Starting spice

In order to start Spice, ssh into the robot with `ssh root@{IP}`. Execute the following commands:

```bash
$ cd /data/user_storage
$ uvicorn app:app --reload --host=0.0.0.0
```

This will start Spice on the robot's raspberry pi. After a few seconds, you can visit the API's swagger docs in the browser at http://{IP}:8000/docs.

### Adding SSH keys to Opentrons

If you can't ssh into the opentrons robot, it is likely because you haven't added your ssh key. Follow the guide [here](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-20) to get a RSA ssh key (the robot's embedded software is not compatible with more modern keys like ed25519). 

The robot does not allow users to directly ssh into it, but this can be circumvented easily. In the official opentrons app, there should be an "open jupyter notebook" option. Open the jupyter notebook into your browser. We will be using the jupyter notebook to execute bash commands.

First, copy your public ssh key (id_rsa.pub in your .ssh directory). Paste that into the following command, replacing {sshkey}, and execute the full command in the jupyter notebook. Keep the quotation marks around the ssh key.

`!echo "{sshkey}" >> /root/.ssh/authorized_keys`

You should now be able to ssh into the robot.

## Updating spice

In order to update Spice with a new app version, simply copy `app.py` to the opentrons (you may have to reload Spice).

```bash
scp app.py root@{ip}:/data/user_storage
```


