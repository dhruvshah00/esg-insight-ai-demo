// Importing required modules and components
"use client";
import { useState, useEffect } from 'react';
import styles from './page.module.css';
import ReactMarkdown from 'react-markdown';

export default function Home() {
  // State variables to manage input values, file uploads, progress tracking, and UI behavior
  const [companyName, setCompanyName] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [reportDetails, setReportDetails] = useState<any[]>([]);
  const [isResponseRequired, setIsResponseRequired] = useState(false);
  const [isCommentBoxVisible, setIsCommentBoxVisible] = useState(false);
  const [userComment, setUserComment] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentLoadingMessage, setCurrentLoadingMessage] = useState('');

  // Function to handle the form submission to generate the report
  const handleGenerateReport = (e: React.FormEvent) => {
    e.preventDefault();
    setReportDetails([]);

    if (uploadedFiles.length > 0) {
      // Preparing FormData with company name and uploaded files
      const formData = new FormData();
      formData.append('company_name', companyName);

      uploadedFiles.forEach((file, index) => {
        formData.append('files', file);
      });

      // Sending file upload request to server
      fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      })
        .then(response => {
          if (!response.ok) {
            throw new Error('File upload failed');
          }
          return response.json();
        })
        .then(data => {
          console.log('File upload success:', data);
        })
        .catch(error => {
          console.error('File upload error:', error);
        });
    } else {
      console.error('No files selected');
      setReportDetails(prev => [...prev, 'Error: No files selected']);
    }

    // WebSocket connection to handle server responses for the query
    const socket = new WebSocket('ws://localhost:8000/query');

    socket.onopen = () => {
      setIsLoading(true);
      socket.send(JSON.stringify({ company_name: companyName }));
    };

    // Handling messages from the WebSocket
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received:', data);
      if (data.type === 'progress') {
        setCurrentLoadingMessage(data.payload);
      } else if (data.type === 'company_details') {
        setIsLoading(false);
        const { gics_sector, gics_industry_group, gics_industry, company_description } = data.payload;
        // Constructing company details section
        const companyDetails = (
          <div className={styles.company_details}>
            <h4>Company Details</h4>
            <hr className={styles.separator} />
            <div className={styles.detail_item}>
              <strong>GICS Sector:</strong> <span>{gics_sector}</span>
            </div>
            <div className={styles.detail_item}>
              <strong>GICS Industry Group:</strong> <span>{gics_industry_group}</span>
            </div>
            <div className={styles.detail_item}>
              <strong>GICS Industry:</strong> <span>{gics_industry}</span>
            </div>
            <hr className={styles.separator} />
            <div className={styles.detail_item_description}>
              <strong>Description:</strong>
              <p>{company_description}</p>
            </div>
          </div>
        );
        setReportDetails(prev => [...prev, companyDetails]);
      } else if (data.type === 'input_required_company_details') {
        setReportDetails(prev => [...prev, data.payload]);
        setIsResponseRequired(true);
      } else if (data.type === 'gri_topics') {
        setIsLoading(false);
        // Constructing GRI topics section
        const griTopics = data.payload;
        const formattedTopics = (
          <div className={styles.topicsContainer}>
            <h4>GRI Topics</h4>
            <hr className={styles.separator} />
            <ul className={styles.listIndented}>
              {griTopics.map((topic: string, index: number) => (
                <li key={index}>{topic}</li>
              ))}
            </ul>
          </div>
        );
        setReportDetails(prev => [...prev, formattedTopics]);
      }
      // Handling additional data types here...
    };

    // Handling WebSocket errors
    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setReportDetails(prev => [...prev, `Error: ${error}`]);
    };

    // Handling WebSocket connection closure
    socket.onclose = () => {
      console.log('WebSocket connection closed');
      setReportDetails(prev => [...prev, 'End of Report']);
    };

    // Keeping a reference to the socket for future interactions
    window.socket = socket;
  };

  // Handling file selection for uploading
  const handleFileSelection = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setUploadedFiles(selectedFiles);
  };

  // Handling user responses to required input prompts (e.g., Yes/No)
  const handleUserResponse = (response: 'yes' | 'no') => {
    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      if (response === 'yes') {
        setIsLoading(true);
        window.socket.send(JSON.stringify({ response }));
        setIsResponseRequired(false);
        setIsCommentBoxVisible(false);
        setReportDetails(prev => prev.slice(0, -1));
      } else {
        setIsCommentBoxVisible(true);
      }
    } else {
      console.error('WebSocket is not connected');
      setReportDetails(prev => [...prev, 'Error: WebSocket is not connected']);
    }
  };

  // Handling comment submission by the user
  const handleSubmitComment = () => {
    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      window.socket.send(JSON.stringify({ response: 'no', comment: userComment }));
      setIsResponseRequired(false);
      setIsCommentBoxVisible(false);
      setUserComment('');
      setReportDetails(prev => prev.slice(0, -2));
    } else {
      console.error('WebSocket is not connected');
      setReportDetails(prev => [...prev, 'Error: WebSocket is not connected']);
    }
  };

  // Returning the main UI of the application
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.appTitle}>ESG Insight AI</h1>
      </header>
      <form onSubmit={handleGenerateReport} className={styles.form}>
        <input
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="Enter Company Name"
          className={styles.input}
        />
        <div className={styles.fileUploadContainer}>
          <input
            id="fileInput"
            type="file"
            multiple
            onChange={handleFileSelection}
            className={styles.fileInput}
          />
        </div>
        <button type="submit" className={styles.button}>Generate</button>
      </form>

      <div id="progress" className={styles.progress}>
        <h3>ESG Materiality Insights:</h3>
        {reportDetails.map((message, index) => (
          <div key={index} className={styles.message}>
            {message}
          </div>
        ))}
        {isResponseRequired && (
          <div className={styles.responseButtons}>
            <button onClick={() => handleUserResponse('yes')} className={styles.button}>Yes</button>
            <button onClick={() => handleUserResponse('no')} className={styles.button}>No</button>
          </div>
        )}
        {isCommentBoxVisible && (
          <div className={styles.commentBox}>
            <textarea
              value={userComment}
              onChange={(e) => setUserComment(e.target.value)}
              placeholder="Please provide your comments"
              className={styles.textarea}
            />
            <button onClick={handleSubmitComment} className={styles.button}>
              Submit Comment
            </button>
          </div>
        )}
        {isLoading && (
          <div className={styles.loadingContainer}>
            <div className={styles.spinner}></div>
            <span className={styles.loadingMessage}>{currentLoadingMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Component for displaying topic assessments
function TopicAssessment({ gri_topic, reporting_requirements, assesment, source_texts }: any) {
  const [isCollapsed, setIsCollapsed] = useState(true);

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  return (
    <div className={styles.topicAssessment}>
      <div className={styles.griTopic}>
        <h3>{gri_topic}</h3>
      </div>
      <hr className={styles.separator} />

      <div className={styles.requirementsAndAssessment}>
        <div className={styles.reportingRequirements}>
          <h4>Reporting Requirements</h4>
          <ReactMarkdown>{reporting_requirements}</ReactMarkdown>
        </div>

        <div className={styles.assessment}>
          <h4>Assessment</h4>
          <ReactMarkdown>{assesment}</ReactMarkdown>
        </div>
      </div>

      <div className={styles.sourceTexts}>
        <button
          className={`${styles.collapseButton} ${isCollapsed ? styles.collapsed : ''}`}
          onClick={toggleCollapse}
        >
          {isCollapsed ? 'View Source Texts' : 'Hide Source Texts'}
        </button>
        {!isCollapsed && (
          <ul className={styles.customUl}>
            {source_texts.map((text: string, index: number) => (
              <li key={index}>
                <ReactMarkdown>{text}</ReactMarkdown>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
