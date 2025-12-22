import React from 'react';
import PublicLayout from '../components/public/PublicLayout';

const PrivacyPolicyPage: React.FC = () => {
    return (
        <PublicLayout>
            <div className="bg-white">
                <div className="max-w-3xl mx-auto px-4 py-12">
                    <h1 className="text-3xl font-bold text-gray-900 mb-8">Privacy Policy</h1>

                    <div className="prose prose-indigo max-w-none text-gray-500">
                        <p className="mb-4">
                            Last updated: {new Date().toLocaleDateString()}
                        </p>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">1. Information We Collect</h2>
                        <p className="mb-4">
                            We collect information that you provide directly to us when you use the Model Risk Management (MRM) system,
                            including your name, email address, role, and any data related to model submissions, validations, and approvals.
                        </p>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">2. How We Use Your Information</h2>
                        <p className="mb-4">
                            We use the information we collect to:
                        </p>
                        <ul className="list-disc pl-5 mb-4 space-y-2">
                            <li>Provide, maintain, and improve the MRM system</li>
                            <li>Process model submissions and validation workflows</li>
                            <li>Send you technical notices, updates, security alerts, and support messages</li>
                            <li>Monitor and analyze trends, usage, and activities in connection with our services</li>
                        </ul>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">3. Data Security</h2>
                        <p className="mb-4">
                            We implement appropriate technical and organizational measures to protect the security of your personal information.
                            However, please be aware that no method of transmission over the Internet or method of electronic storage is 100% secure.
                        </p>

                        <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">4. Contact Us</h2>
                        <p className="mb-4">
                            If you have any questions about this Privacy Policy, please contact the Model Risk Management team.
                        </p>
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
};

export default PrivacyPolicyPage;
