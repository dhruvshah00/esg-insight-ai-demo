"use client";
import { useState, useEffect } from 'react';
import styles from './page.module.css';
import ReactMarkdown from 'react-markdown';

export default function Home() {
  const [company_name, setQuery] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState<any[]>([]);
  const [responseRequired, setResponseRequired] = useState(false);
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false); 
  const [loadingMessage, setLoadingMessage] = useState(''); 


  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setProgress([]);

    if (files.length > 0) {
      const formData = new FormData();
      formData.append('company_name', company_name);
  
      files.forEach((file, index) => {
        formData.append('files', file);  
      });
  
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
      setProgress(prev => [...prev, 'Error: No files selected']);
    }

    const socket = new WebSocket('ws://localhost:8000/query');

    socket.onopen = () => {
      setLoading(true);
      socket.send(JSON.stringify({ company_name: company_name }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received:', data);
      if (data.type === 'progress') {
        setLoadingMessage(data.payload);
      } else if (data.type === 'company_details') {
        setLoading(false);
        const { gics_sector, gics_industry_group, gics_industry, company_description } = data.payload;
        const companyDetails = (
        <div className={styles.company_details}>
          <h4>Company Details</h4>
          <hr className={styles.separator}/>
          <div className={styles.detail_item}>
            <strong>GICS Sector:</strong> <span>{gics_sector}</span>
          </div>
          <div className={styles.detail_item}>
            <strong>GICS Industry Group:</strong> <span>{gics_industry_group}</span>
          </div>
          <div className={styles.detail_item}>
            <strong>GICS Industry:</strong> <span>{gics_industry}</span>
          </div>
          <hr className={styles.separator}/>
          <div className={styles.detail_item_description}>
            <strong>Description:</strong>
            <p>{company_description}</p>
          </div>
        </div>
        );
        setProgress(prev => [...prev, companyDetails]);
      } else if (data.type === 'input_required_company_details') {
        setProgress(prev => [...prev, data.payload]);
        setResponseRequired(true);
      } else if (data.type === 'gri_topics') {
        setLoading(false);
        const griTopics = data.payload;
        const formattedTopics = (
          <div className={styles.topicsContainer}>
            <h4>GRI Topics</h4>
            <hr className={styles.separator}/>
            <ul className={styles.listIndented}>
              {griTopics.map((topic: string, index: number) => (
                <li key={index}>{topic}</li>
              ))}
            </ul>
          </div>
        );
        setProgress(prev => [...prev, formattedTopics]);
      } else if (data.type === 'input_required_gri_topics') {
        setProgress(prev => [...prev, data.payload]);
        setResponseRequired(true);
      } else if (data.type === 'topic_assesment') {
        setLoading(false);
        const { gri_topic, reporting_requirements, assesment, source_texts } = data.payload;
        const topicAssessment = (
          <TopicAssessment 
            gri_topic={gri_topic} 
            reporting_requirements={reporting_requirements} 
            assesment={assesment} 
            source_texts={source_texts} 
          />
        );
        setProgress(prev => [...prev, topicAssessment]);
      } else if (data.type === 'un_sdg_list') {
        const unSDGList = data.payload;
        const formattedSDGList = (
          <div className={styles.topicsContainer}>
            <h4>UN Sustainable Development Goals</h4>
            <hr className={styles.separator}/>
            <ul className={styles.listIndented}>
              {unSDGList.map((goal: string, index: number) => (
                <li key={index}>{goal}</li>
              ))}
            </ul>
          </div>
        );
        
        setProgress(prev => [...prev, formattedSDGList]);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setProgress(prev => [...prev, `Error: ${error}`]);
    };

    socket.onclose = () => {
      console.log('WebSocket connection closed');
      setProgress(prev => [...prev, 'End of Report']);
    };

    window.socket = socket;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(selectedFiles);
  };

  const handleResponse = (response: 'yes' | 'no') => {
    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      if (response === 'yes') {
        setLoading(true);
        window.socket.send(JSON.stringify({ response }));
        setResponseRequired(false);
        setShowCommentBox(false);
        setProgress(prev => prev.slice(0, -1));
      } else {
        setShowCommentBox(true);
      }
    } else {
      console.error('WebSocket is not connected');
      setProgress(prev => [...prev, 'Error: WebSocket is not connected']);
    }
  };

  const handleSubmitComment = () => {
    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      window.socket.send(JSON.stringify({ response: 'no', comment }));
      setResponseRequired(false);
      setShowCommentBox(false);
      setComment('');
      setProgress(prev => prev.slice(0, -2));
    } else {
      console.error('WebSocket is not connected');
      setProgress(prev => [...prev, 'Error: WebSocket is not connected']);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.appTitle}>ESG Insight AI</h1>
      </header>
      <form onSubmit={handleSubmit} className={styles.form}>
        <input
          type="text"
          value={company_name}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter Company Name"
          className={styles.input}
        />
        <div className={styles.fileUploadContainer}>
          <input
            id="fileInput"
            type="file"
            multiple
            onChange={handleFileChange}
            className={styles.fileInput}
          />
        </div>
        <button type="submit" className={styles.button}>Generate</button>
      </form>
      <div id="progress" className={styles.progress}>
        <h3>ESG Materiality Insights:</h3>
        {progress.map((message, index) => (
          <div key={index} className={styles.message}>
            {message}
          </div>
        ))}
        {responseRequired && (
          <div className={styles.responseButtons}>
            <button onClick={() => handleResponse('yes')} className={styles.button}>Yes</button>
            <button onClick={() => handleResponse('no')} className={styles.button}>No</button>
          </div>
        )}
        {showCommentBox && (
          <div className={styles.commentBox}>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Please provide your comments"
              className={styles.textarea}
            />
            <button onClick={handleSubmitComment} className={styles.button}>
              Submit Comment
            </button>
          </div>
        )}
        {loading && (
          <div className={styles.loadingContainer}>
            <div className={styles.spinner}></div>
            <span className={styles.loadingMessage}>{loadingMessage}</span>
          </div>
        )}
      </div>
    </div>
  );
}

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
      <hr className={styles.separator}/>

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
