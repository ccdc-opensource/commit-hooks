using System;

namespace Ccdc.CommitHooks
{
    interface CommitHookCheckInterface
    {
        // This runs on the client side
        bool clientSideCheck();
        // This runs in github actions
        bool githubSideCheck();
    }

}
