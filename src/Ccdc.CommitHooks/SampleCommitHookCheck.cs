using System;

namespace Ccdc.CommitHooks
{

    public class SampleCommitHookCheck : CommitHookCheckInterface
    {
        public bool clientSideCheck()
        {
            return false;
        }
        public bool githubSideCheck()
        {
            return false;
        }
    }
}
